#!/bin/bash
# 测试脚本：验证所有优化改进

set -e

echo "================================"
echo "Open Image 优化改进测试套件"
echo "================================"
echo ""

SCRIPT_PATH="skills/open-image/scripts/open_image.py"
OUTPUT_DIR="test_output"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

echo "1. 测试基本文生图功能"
echo "--------------------------------"
python "$SCRIPT_PATH" generate \
  --prompt "a cute orange cat sitting on a windowsill" \
  --quality low \
  --size 1024x1024 \
  --output-dir "$OUTPUT_DIR" \
  --count 1

echo ""
echo "✓ 基本文生图测试完成"
echo ""

echo "2. 测试批量生成（验证进度反馈和 as_completed）"
echo "--------------------------------"
python "$SCRIPT_PATH" batch \
  --prompt "a serene mountain landscape" \
  --prompt "a vibrant city street at night" \
  --output-dir "$OUTPUT_DIR"

echo ""
echo "✓ 批量生成测试完成"
echo ""

echo "3. 测试实验分辨率警告"
echo "--------------------------------"
python "$SCRIPT_PATH" generate \
  --prompt "test image" \
  --quality low \
  --size 2560x1440 \
  --output-dir "$OUTPUT_DIR" \
  --count 1

echo ""
echo "✓ 实验分辨率测试完成"
echo ""

echo "4. 测试结果回执功能"
echo "--------------------------------"
RESULT_FILE="$OUTPUT_DIR/result.json"
python "$SCRIPT_PATH" generate \
  --prompt "test receipt" \
  --quality low \
  --size 1024x1024 \
  --output-dir "$OUTPUT_DIR" \
  --result-file "$RESULT_FILE" \
  --count 1

if [ -f "$RESULT_FILE" ]; then
    echo "结果回执内容："
    cat "$RESULT_FILE" | python -m json.tool
    echo ""
    echo "✓ 结果回执测试完成"
else
    echo "✗ 结果回执文件未生成"
fi

echo ""
echo "5. 测试多图生成（验证进度）"
echo "--------------------------------"
python "$SCRIPT_PATH" generate \
  --prompt "abstract art" \
  --quality low \
  --size 1024x1024 \
  --output-dir "$OUTPUT_DIR" \
  --count 3

echo ""
echo "✓ 多图生成测试完成"
echo ""

echo "================================"
echo "所有测试完成！"
echo "生成的图片位于: $OUTPUT_DIR"
echo "================================"
