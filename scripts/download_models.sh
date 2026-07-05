#!/usr/bin/env bash
# 下载 MediaPipe 模型到 assets/models/
# 用法：bash scripts/download_models.sh
# 来源：MediaPipe 官方 model registry (Apache 2.0)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MODELS_DIR="$PROJECT_ROOT/assets/models"

mkdir -p "$MODELS_DIR"

# 官方 URL（Google Storage CDN）
BASE="https://storage.googleapis.com/mediapipe-models"

# face_landmarker.task (~3.6 MB)
# hand_landmarker.task (~7.5 MB)
# gesture_recognizer.task (~8 MB)
# blaze_face_short_range.tflite (~225 KB, 备用)

declare -A MODELS=(
  ["face_landmarker.task"]="$BASE/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
  ["hand_landmarker.task"]="$BASE/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
  ["gesture_recognizer.task"]="$BASE/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"
)

# 可选备用：blaze_face_short_range.tflite（直接从 MediaPipe-Real-Time-Computer-Vision-Demos 仓库下载）
BLAZE_URL="https://raw.githubusercontent.com/yeemachine/mediapipe/main/models/blaze_face_short_range.tflite"

for filename in "${!MODELS[@]}"; do
  url="${MODELS[$filename]}"
  target="$MODELS_DIR/$filename"
  if [ -f "$target" ]; then
    echo "✔ $filename 已存在，跳过"
    continue
  fi
  echo "↓ 下载 $filename from $url"
  if ! curl -sSL -o "$target" "$url"; then
    echo "✗ 下载失败：$filename" >&2
    rm -f "$target"
    exit 1
  fi
  size=$(stat -c%s "$target" 2>/dev/null || stat -f%z "$target")
  echo "  → $size bytes"
done

# blaze_face_short_range.tflite
target="$MODELS_DIR/blaze_face_short_range.tflite"
if [ -f "$target" ]; then
  echo "✔ blaze_face_short_range.tflite 已存在，跳过"
else
  echo "↓ 下载 blaze_face_short_range.tflite from $BLAZE_URL"
  if ! curl -sSL -o "$target" "$BLAZE_URL"; then
    echo "✗ 下载失败：blaze_face_short_range.tflite" >&2
    rm -f "$target"
    exit 1
  fi
fi

echo
echo "✓ 全部模型就绪："
ls -lh "$MODELS_DIR"