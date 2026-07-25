# Watermark Remover Auto V2 - Tunable Parameters

## Detection Thresholds

### Pink Rectangles (Lines 654-656)
lower_pink = np.array([165, 110, 110])  # HSV lower bound - increase to be stricter
upper_pink = np.array([180, 255, 255])  # HSV upper bound
# Line 674: if area > 300  # Minimum area in pixels - increase to ignore smaller regions

### Color Shapes (Lines 695-696)
edges = cv2.Canny(corner_gray, 60, 160, apertureSize=3)  # Edge detection thresholds
# Line 700: if area < 300 or area > (width * height * 0.08)  # Min/max area filtering
# Line 705: if 0.4 <= aspect_ratio <= 2.5  # Width/height ratio range for rectangles

### Text Watermarks (OCR) (Lines 745-746, 749-750)
if confidence > 0.75:  # EasyOCR confidence threshold (0.0-1.0) - higher = stricter
    bx = max(0, np.min(points[:, 0]) - 12)  # Padding around detected text
    by = max(0, np.min(points[:, 1]) - 12)  # Increase for larger inpaint area
    bw = min(corner.shape[1] - bx, np.max(points[:, 0]) - bx + 24)
    bh = min(corner.shape[0] - by, np.max(points[:, 1]) - by + 24)

# Line 761: if confidence > 70 and text  # Pytesseract confidence (0-100)
# Lines 763-766: Same padding values as above

### Semi-Transparent (Lines 793-794)
bright_mask = cv2.inRange(corner_gray, 185, 255)  # Brightness threshold for white text
edges = cv2.Canny(corner_gray, 40, 110)  # Edge detection for watermark outlines

# Line 797: kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))  # Morphology kernel size
# Line 806: if area > 80  # Minimum contour area
# Line 823: if (ratio > 1.5 and area > 120 and area < 4500) or (ratio > 3.0 and area > 80)
#           ^ Aspect ratio + area ranges for watermark filtering

## General Settings

### Mask Padding (Line 857)
pad = 10  # Padding around all detected regions - increase for larger inpaint area

### Batch Sizes (Lines 162-167 in process_images_batch)
if inpaint_method == "lama_ai":
    batch_size = 2  # Images per batch for AI method
elif detection_mode in ["text_watermarks", "combo_aggressive"]:
    batch_size = 3  # For OCR-heavy modes
else:
    batch_size = 5  # For faster modes

### Overlap Detection (Line 829 in _remove_overlapping_bboxes)
def _remove_overlapping_bboxes(bboxes, overlap_threshold: float = 0.5)
# overlap_threshold: 0.0-1.0, higher = more strict deduplication

## Quick Tuning Guide

**OCR getting false positives?**
- Line 745: Increase `0.75` to `0.85` or `0.9`
- Line 761: Increase `70` to `80` or `85`

**OCR missing watermarks?**
- Lines 749-750, 763-766: Increase padding from `12/24` to `15/30` or `20/40`
- Line 857: Increase general padding from `10` to `15` or `20`

**Semi-transparent too aggressive?**
- Line 793: Increase `185` to `190` or `195` (stricter brightness)
- Line 806: Increase `80` to `100` or `120` (ignore smaller regions)
- Line 823: Adjust area ranges to be more restrictive

**Detection too sensitive?**
- Increase minimum area thresholds (lines 674, 700, 806, 823)
- Narrow aspect ratio ranges (line 705)
- Increase edge detection thresholds (lines 695, 794)

**Detection missing watermarks?**
- Decrease confidence thresholds
- Increase padding values
- Widen HSV/brightness ranges
- Decrease minimum area thresholds