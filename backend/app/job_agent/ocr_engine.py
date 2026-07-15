import os

_ocr_instance = None

def get_ocr_instance():
    global _ocr_instance
    if _ocr_instance is None:
        # Disable oneDNN and MKLDNN to bypass NotImplementedError ConvertPirAttribute2RuntimeAttribute bugs on CPU
        os.environ["FLAGS_use_onednn"] = "0"
        os.environ["FLAGS_use_mkldnn"] = "0"
        os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"
        
        from paddleocr import PaddleOCR
        print("[OCR ENGINE] Initializing PaddleOCR instance (first-run compile)...")
        _ocr_instance = PaddleOCR(use_angle_cls=True, lang='en')
    return _ocr_instance

def run_paddle_ocr_for_job(image_path: str) -> str:
    try:
        ocr = get_ocr_instance()
        result = ocr.ocr(image_path)
        if not result or not result[0]:
            return ""
        texts = [line[1][0] for line in result[0]]
        return "\n".join(texts)
    except Exception as e:
        print(f"[OCR ENGINE ERROR] Failed to run OCR on {image_path}: {e}")
        import traceback
        traceback.print_exc()
        return ""
