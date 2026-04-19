# BERT 联合意图与槽位识别（训练 / PyTorch 推理 / QNN 量化上板）

本仓库实现基于 **BERT** 的 **自然语言理解（NLU）** 联合模型：对单条用户话语同时预测 **意图（intent）** 与 **槽位填充（slot filling）**。思路与 [JoinBERT](https://arxiv.org/abs/1902.10909) 相近：共享 BERT 编码器，用 `[CLS]` 经 pooler 的句向量做意图分类，用各 token 的 hidden state 做 BIO 序列标注，再通过 `JointIntentSlotDetector` 将 BIO 标签解码为 `{槽位名: [槽值, ...]}` 字典。

业务数据示例见 `data/cabin/`（座舱语音指令等多版本数据集）；参考学术数据见 `data/SMP2019/`。

---

## 目录结构（核心代码）

| 路径 | 说明 |
|------|------|
| `models.py` | `JointBert`：1 个意图头 + 1 个槽位头，联合交叉熵损失 |
| `datasets.py` | `IntentSlotDataset`：JSON → token 对齐的槽位 BIO 标签 |
| `train.py` | 训练、每 epoch 验证、保存 best intent acc 权重与评测曲线 |
| `detector.py` | `JointIntentSlotDetector`：加载权重后 `detect(text)` 推理 |
| `labeldict.py` | 意图/槽位标签与 id 互转 |
| `tools.py` | 保存 tokenizer / 模型目录 |
| `train.sh` | 训练命令示例（座舱 V8 等） |
| `test.py` | **仅评测**脚本（文件内示例仍写 `eval.py`，实际入口为 `python test.py`） |
| `bert_export_onnx.py` | **QNN Step 1**：仅导出 BERT **编码器** 为 ONNX，并生成校准用 raw |
| `qwen3_vl-main/example2/host_linux/qnn_model_prepare_bert_8775.py` | **QNN Step 2**：ONNX → DLC → PTQ 量化 → HTP Context Binary |
| `eval_v6_joint_qnn.py` | **QNN Step 3**：`qnn-net-run` 取 encoder 输出 + PyTorch 上跑分类头，对齐评测 |
| `run_qnn_bert_pipeline.sh` | 串联环境变量与 Step 3 的示例 Shell（**其中 Step 1/2 的 `python` 行默认被注释**，需按需打开） |
| `qnn-r23600.1/` | 本地 QNN SDK 根目录示例（可通过环境变量指向其他安装路径） |
| `transformers-4.27.4/`、`transformers-4.57.1/` | 随仓库的 Transformers 源码/版本（训练与 QNN 工具链可能对版本有不同要求，见下文） |

---

## 运行环境（PyTorch 训练）

典型配置（与历史 README 一致，可按机器调整）：

- Python 3.8+（若使用 AIMET / 较新 QNN 配套脚本，常见为 **Python 3.10** 与 **PyTorch 2.1.x**）
- PyTorch 1.10+（或 2.x，需与 `transformers` 版本匹配）
- Huggingface Transformers（训练常用 4.x；`bert_export_onnx.py` 注释中说明 BERT 与 **AIMET Pro 1.35** 等场景可能锁在 **4.27.x**）
- 其他：`numpy`、`tqdm`；训练曲线与混淆矩阵需 `matplotlib`；完整分类报告需 `sklearn`

安装示例：

```bash
pip install torch transformers tqdm numpy matplotlib scikit-learn safetensors onnxruntime
```

---

## 数据准备

训练依赖三类文件。

### 1. 训练/测试 JSON

列表格式，每条至少包含：

- `text`：用户话语  
- `intent`：意图字符串（须在意图标签表内或可映射到 `[UNK]`）  
- `slots`：`{ "槽位名": "槽值" }` 或 `{ "槽位名": ["值1", "值2"] }`  

示例：

```json
{
  "text": "搜索西红柿的做法。",
  "domain": "cookbook",
  "intent": "QUERY",
  "slots": {"ingredient": "西红柿"}
}
```

可参考 `data/SMP2019/split_data.py` 划分 `split_train.json` / `split_test.json`。

### 2. 意图标签 `intent_labels.txt`

每行一个意图；未知意图用 `[UNK]`（仓库内标签文件使用该占位符命名）。

### 3. 槽位标签 `slot_labels.txt`

包含特殊标签：`[PAD]`、`[UNK]`、`[O]`，以及 `B_槽位名`、`I_槽位名` 等 BIO 标记。

---

## BERT NLU 模型训练

### 训练逻辑概要

1. `IntentSlotDataset` 用 `BertTokenizer` 对 `text` 分词，并根据 `slots` 中子串与 token 对齐生成 BIO 序列（见 `datasets.py` 中 `get_slot_labels`）。  
2. `JointBert` 前向同时优化 **槽位 token 分类损失** 与 **意图分类损失**（权重均为 1）。  
3. 每个 epoch 结束后在 **测试集 JSON** 上用 `JointIntentSlotDetector` 解码，计算意图准确率、槽位 utterance 级 P/R、span F1、token acc 等，并写入 `save_dir`。  
4. 当验证集 **意图准确率** 创新高时，保存 `model/best_intent_acc/`（HuggingFace 格式：`config.json`、`model.safetensors` 等）及混淆矩阵、错例等。

### 命令行示例

```bash
python train.py \
  --cuda_devices 0 \
  --tokenizer_path "bert-base-chinese" \
  --model_path "bert-base-chinese" \
  --train_data_path "data/cabin/V6/split_train.json" \
  --test_data_path "data/cabin/V6/split_test.json" \
  --intent_label_path "data/cabin/V6/intent_labels.txt" \
  --slot_label_path "data/cabin/V6/slot_labels.txt" \
  --save_dir "saved_models/V6" \
  --batch_size 32 \
  --train_epochs 5 \
  --logging_steps 30 \
  --saving_steps 0 \
  --saving_epochs 0
```

说明：

- `--saving_steps 0` 与 `--saving_epochs 0`：关闭按步/按 epoch 例行存盘；**仅在 best intent accuracy 时** 存最佳模型（见 `train.py` 中 `save_best_intent_artifacts`）。  
- `--max_training_steps`：大于 0 时作为优化器总步数（用于 linear warmup 调度）。  
- `--gradient_accumulation_steps`：梯度累积。  
- `CUDA_VISIBLE_DEVICES` 由 `--cuda_devices` 在脚本开头写入。

项目内 `train.sh` 为另一组超参示例（大 batch、指定数据版本），可直接修改路径后执行：`bash train.sh`。

### 训练产物（`save_dir`）

常见包括：

- `tokenizer/`：与训练一致的 tokenizer  
- `model/best_intent_acc/`：最佳 JointBERT 权重  
- `train_eval_history.json`、`train_eval_curves.png`：按 epoch 的训练损失与验证指标曲线  
- `intent_confusion_matrix.json`、`*_misclassified_samples.json`、`slot_metrics.json` 等：评测细节（依赖是否安装 sklearn / matplotlib）

---

## PyTorch 意图与槽位推理

训练完成后使用 `JointIntentSlotDetector` 加载模型与标签表（注意 **`intent_label_path` 与 `slot_label_path` 之间应有逗号**，若手写一行调用请勿漏写）。

```python
from detector import JointIntentSlotDetector

model = JointIntentSlotDetector.from_pretrained(
    model_path="saved_models/V6/model/best_intent_acc",
    tokenizer_path="saved_models/V6/tokenizer",  # 训练时 save_module(..., additional_name="") 写入的目录
    intent_label_path="data/cabin/V6/intent_labels.txt",
    slot_label_path="data/cabin/V6/slot_labels.txt",
)
print(model.detect("西红柿的做法是什么"))
# 示例输出: {"text": "...", "intent": "QUERY", "slots": {"ingredient": ["西红柿"]}}
```

`detect` 默认对英文大小写可转小写（`str_lower_case=True`）；batch 可传入字符串列表。

---

## 仅评测（不训练）

对已保存 checkpoint 在测试集上复现指标（不写回训练权重）：

```bash
python test.py \
  --cuda_devices "0" \
  --tokenizer_path "bert-base-chinese" \
  --model_ckpt "saved_models/V6/model/best_intent_acc" \
  --test_data_path "data/cabin/V6/split_test.json" \
  --intent_label_path "data/cabin/V6/intent_labels.txt" \
  --slot_label_path "data/cabin/V6/slot_labels.txt" \
  --save_dir "saved_models/V6/eval_only"
```

具体参数以 `test.py` 内 `argparse` 为准。

---

## QNN 量化与上板（高通 HTP 链路）

本项目的 **设备侧部署策略** 是：**把 BERT 编码器（`BertModel`，输出 `last_hidden_state`）放到 QNN/DLC 中运行**；**意图线性头与槽位线性头仍在 PyTorch（主机 CPU/GPU）上执行**。这样可复用训练得到的 `seq_heads.0` 与 `token_heads.0` 权重，并与 `eval_v6_joint_qnn.py` 中的参考实现一致。

整体流程：

```mermaid
flowchart LR
  A[训练 JointBert] --> B[bert_export_onnx.py]
  B --> C[qnn_model_prepare_bert_8775.py]
  C --> D[Context Binary .serialized.bin]
  D --> E[qnn-net-run HTP 模拟或真机]
  E --> F[encoder 输出 hidden]
  F --> G[PyTorch Intent/Slot 头]
  G --> H[意图 + BIO + 槽值解码]
```

### Step 1：导出 ONNX（`bert_export_onnx.py`）

从已保存的 JointBERT 目录（含 `config.json`、`model.safetensors`）加载 **底层 `BertModel`**，包装为 `BertEncoderForQNN`：

- **输入（固定 seq_len，与训练 max_length 对齐）**：`attention_mask`（**uint8**）、`input_ids`、`token_type_ids`（int32）；ONNX 中 `attention_mask` 在 wrapper 内转为 float 再送入 BERT，便于与 HTP 上 1 byte/token 的 mask 约定对齐。  
- **输出**：`last_hidden_state`。

同时生成 `base/test_vectors/raw_inputs/` 下的 `.raw` 与 `input_list.txt`，供 **qairt-quantizer** 做 PTQ 校准。

示例：

```bash
python bert_export_onnx.py \
  --model-dir saved_models/V6/model/best_intent_acc \
  --output-dir qwen3_vl-main/example1/outputs/step1_bert \
  --calib-json data/cabin/V6/split_train.json \
  --calib-samples 65535 \
  --seq-len 64 \
  --name best_intent_acc
```

可选 `--use-aimet`：用 AIMET `QuantizationSimModel` 导出带 `.encodings` 的 ONNX（需正确安装 AIMET / **避免与 PyPI `aimet-torch` 混装**，详见脚本内说明）。若环境与 Transformers 版本冲突，可仅用 PTQ：`run_qnn_bert_pipeline.sh --no-aimet` 思路。

导出后可用脚本内 **OnnxRuntime** 与 PyTorch 对比数值（`--skip-verify` 可关闭）。

### Step 2：ONNX → DLC → 量化 → Context Binary（`qnn_model_prepare_bert_8775.py`）

在配置好 **QNN SDK**（例如 `qnn-r23600.1`，或设置 `QNN_SDK_ROOT`）与 Example1 输出目录后，在 `qwen3_vl-main/example2/host_linux/` 下执行准备脚本。脚本会调用 **qairt-converter**、**qairt-quantizer**、**qnn-context-binary-generator** 等工具（具体以脚本为准），生成可在 **HTP** 上加载的 **serialized context binary**。

常用环境变量（与 `run_qnn_bert_pipeline.sh` 一致，可按需覆盖）：

| 变量 | 含义 |
|------|------|
| `QNN_SDK_ROOT` | QNN SDK 根目录 |
| `INPUT_MODEL_DIR` | Step1 输出根目录（内含 `base/onnx/`） |
| `ONNX_NAME` | ONNX 文件名前缀（如 `best_intent_acc`） |
| `ACT_BITWIDTH` / `WEIGHTS_BITWIDTH` | 激活 / 权重量化位宽（脚本顶部注释讨论过 8/16bit 与 HTP 兼容性，以当前 SDK 与报错为准） |
| `QUANT_CALIB_JSON` / `QUANT_CALIB_SAMPLES` / `QUANT_CALIB_SEQ_LEN` | 校准数据与条数、序列长度 |
| `MODEL_ID` | 用于 tokenizer 与校准文本编码的模型目录（通常与 Step1 的 `--model-dir` 一致） |
| `BERT_QNN_CONVERTER_NO_QUANT_OVERRIDES` | 为 `1` 时 converter 不传 `--quantization_overrides`（无 AIMET encodings 时常用） |

默认产物路径示例：

`qwen3_vl-main/example2/host_linux/outputs/step2_bert/assets/bert/binaries/<ONNX_NAME>_socid52_archv73.serialized.bin`

**SoC / DSP 架构**（如 `HTP_SOC_ID`、`HTP_DSP_ARCH`）需与你的芯片与 QNN 发布说明一致；脚本名中 `8775` 表示与 SA8775P 等目标对齐的示例配置。

### Step 3：x86 HTP 模拟评测（`eval_v6_joint_qnn.py`）

对测试集逐条（或 batch 策略见脚本）构造 raw 输入，调用 **`qnn-net-run`** 得到量化 encoder 的 `last_hidden_state`，再用从 `model.safetensors` 抽出的 **intent/slot 线性层** 计算 logits，与全精度 PyTorch 流水线对比，输出意图准确率、槽位 span F1 等，并写入 `--work-dir`（默认 `qnn_eval_joint_output/report/summary.json`）。

注意：

- **`qnn-net-run`** 默认建议 **`--use_native_input_files`**，按各输入真实 dtype 读入 `.raw`。  
- 当激活为 **16bit** 等导致 `attention_mask` 在图上是 **uint16** 时，评测脚本提供 **`--mask-raw-uint16`**（`run_qnn_bert_pipeline.sh` 在 `ACT_BITWIDTH=16` 时会自动追加）。8bit 量化 DLC 时不要误开。

示例：

```bash
python eval_v6_joint_qnn.py \
  --model-dir saved_models/V6/model/best_intent_acc \
  --context-bin qwen3_vl-main/example2/host_linux/outputs/step2_bert/assets/bert/binaries/best_intent_acc_socid52_archv73.serialized.bin \
  --test-json data/cabin/V6/split_test.json \
  --intent-labels data/cabin/V6/intent_labels.txt \
  --slot-labels data/cabin/V6/slot_labels.txt \
  --qnn-sdk-root qnn-r23600.1 \
  --seq-len 64 \
  --work-dir qnn_eval_joint_output
```

### 一键脚本 `run_qnn_bert_pipeline.sh`

该脚本用于统一 **环境变量** 与 **Step 3** 调用；仓库中 **Step 1、Step 2 的 `python ...` 行当前为注释状态**，完整跑通管线时请：

1. 编辑脚本中的 `ROOT_DIR`、`MODEL_DIR`、`QNN_SDK_ROOT`、`STEP1_OUTPUT`、`STEP2_DIR` 等，使其指向本机路径；  
2. 取消注释 `bert_export_onnx.py` 与 `qnn_model_prepare_bert_8775.py` 的调用行；  
3. 在已激活的 conda 环境（脚本注释中的 `qnn_llm` 等）下执行：`bash run_qnn_bert_pipeline.sh [--use-aimet|--no-aimet] [--seq-len 64]`。

脚本内 `MAX_QUALITY=1` 与 `MAX_QUALITY=0` 会切换校准样本数、权重量化位宽、评测条数、`qnn-net-run` profiling 等默认值。

### 真机「上板」

在 **x86 模拟验证**通过后，将 Step 2 生成的 **context binary**、标签文件、tokenizer 及端侧推理代码（调用 QNN 运行时加载 context、执行推理、再在 CPU 上跑两个小头或使用等价 C++ 矩阵乘）集成到 **Android / Linux Embedded** 等目标。具体 API 以 **Qualcomm AI Engine Direct / QNN** 文档与平台 BSP 为准；本仓库提供的是 **模型准备与精度对齐评测** 参考实现。

---

## 常见问题

1. **训练与 QNN 脚本 Transformers 版本不一致**  
   训练可用较新 4.x；AIMET 或旧 QNN 示例可能要求 4.27.x。建议 **分 conda 环境** 分别跑训练与导出/量化。

2. **JointBERT 与纯 BertModel 导出**  
   Step1 仅导出 **BertModel**；意图/槽位头在 Step3 用 safetensors 单独加载。若你改动了 `models.py` 结构，需同步修改 `eval_v6_joint_qnn.py` 中的权重键名（如 `seq_heads.0` / `token_heads.0`）。

3. **`run_qnn_bert_pipeline.sh` 直接跑只有 Step3**  
   若未事先生成 context binary，Step3 会失败；请先完成 Step1+Step2 或取消注释一键跑。

---

## 引用

- JoinBERT: [A Joint Model for Intent Detection and Slot Filling](https://arxiv.org/abs/1902.10909)  
- SMP2019 评测相关数据见 [SMP2019 会议](https://conference.cipsc.org.cn/smp2019/)
