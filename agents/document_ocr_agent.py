"""
Document OCR Agent
Performs optical character recognition on document images
"""

import os
import io
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from PIL import Image
import numpy as np

# OCR libraries
try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import easyocr
except ImportError:
    easyocr = None

try:
    import cv2
except ImportError:
    cv2 = None


class DocumentOCRAgent:
    """Agent for performing OCR on document images"""
    
    def __init__(self, ocr_engine: str = 'auto'):
        """
        Initialize OCR agent
        
        Args:
            ocr_engine: OCR engine to use ('tesseract', 'easyocr', 'auto')
        """
        self.ocr_engine = self._select_engine(ocr_engine)
        self.reader = None
        
        if self.ocr_engine == 'easyocr' and easyocr:
            # Initialize EasyOCR reader (supports multiple languages)
            self.reader = easyocr.Reader(['en'], gpu=False)
    
    def _select_engine(self, preference: str) -> str:
        """Select OCR engine based on availability"""
        if preference == 'tesseract' and pytesseract:
            return 'tesseract'
        elif preference == 'easyocr' and easyocr:
            return 'easyocr'
        elif preference == 'auto':
            if easyocr:
                return 'easyocr'
            elif pytesseract:
                return 'tesseract'
        
        return None
    
    def process_document(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a document image with OCR
        
        Args:
            file_path: Path to the document image
            options: OCR options
                - language: Language code (e.g., 'eng', 'fra', 'deu')
                - preprocess: Apply preprocessing (True/False)
                - deskew: Correct image skew
                - denoise: Remove noise
                - enhance_contrast: Enhance image contrast
                - detect_layout: Detect document layout
                - confidence_threshold: Minimum confidence for text
                
        Returns:
            Dictionary containing:
                - text: Extracted text
                - blocks: Text blocks with positions
                - confidence: Overall confidence score
                - metadata: Processing metadata
                - errors: Any errors encountered
        """
        options = options or {}
        result = {
            'text': '',
            'blocks': [],
            'confidence': 0.0,
            'metadata': {},
            'errors': []
        }
        
        if not self.ocr_engine:
            result['errors'].append("No OCR engine available. Install pytesseract or easyocr.")
            return result
        
        try:
            # Load and preprocess image
            image = self._load_image(file_path)
            
            if options.get('preprocess', True):
                image = self._preprocess_image(image, options)
            
            # Perform OCR based on engine
            if self.ocr_engine == 'tesseract':
                result = self._ocr_with_tesseract(image, options)
            elif self.ocr_engine == 'easyocr':
                result = self._ocr_with_easyocr(image, options)
            
            # Detect layout if requested
            if options.get('detect_layout', False):
                result['layout'] = self._detect_layout(image)
            
            result['metadata'] = {
                'engine': self.ocr_engine,
                'image_size': image.shape[:2] if hasattr(image, 'shape') else image.size,
                'preprocessing': options.get('preprocess', True)
            }
            
        except Exception as e:
            result['errors'].append(f"OCR processing error: {str(e)}")
        
        return result
    
    def _load_image(self, file_path: str) -> Any:
        """Load image from file"""
        image = Image.open(file_path)
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array for processing
        if cv2:
            return np.array(image)
        else:
            return image
    
    def _preprocess_image(self, image: Any, options: Dict) -> Any:
        """Preprocess image for better OCR results"""
        if not cv2:
            return image
        
        # Convert PIL Image to numpy array if needed
        if isinstance(image, Image.Image):
            image = np.array(image)
        
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # Denoise
        if options.get('denoise', True):
            gray = cv2.medianBlur(gray, 3)
        
        # Enhance contrast
        if options.get('enhance_contrast', True):
            gray = cv2.adaptiveThreshold(
                gray, 255, 
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
        
        # Deskew
        if options.get('deskew', False):
            gray = self._deskew_image(gray)
        
        return gray
    
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """Correct image skew"""
        if not cv2:
            return image
        
        try:
            # Find contours
            coords = np.column_stack(np.where(image > 0))
            
            # Calculate rotation angle
            angle = cv2.minAreaRect(coords)[-1]
            
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            
            # Rotate image
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                image, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            
            return rotated
        except:
            return image
    
    def _ocr_with_tesseract(self, image: Any, options: Dict) -> Dict:
        """Perform OCR using Tesseract"""
        result = {
            'text': '',
            'blocks': [],
            'confidence': 0.0,
            'errors': []
        }
        
        if not pytesseract:
            result['errors'].append("Tesseract not available")
            return result
        
        try:
            # Convert numpy array to PIL Image if needed
            if isinstance(image, np.ndarray):
                image = Image.fromarray(image)
            
            # Configure Tesseract
            config = '--oem 3 --psm 3'
            lang = options.get('language', 'eng')
            
            # Get text
            result['text'] = pytesseract.image_to_string(
                image, lang=lang, config=config
            )
            
            # Get detailed data
            data = pytesseract.image_to_data(
                image, lang=lang, config=config,
                output_type=pytesseract.Output.DICT
            )
            
            # Extract text blocks with positions
            n_boxes = len(data['text'])
            blocks = []
            confidences = []
            
            for i in range(n_boxes):
                if int(data['conf'][i]) > 0:
                    text = data['text'][i].strip()
                    if text:
                        block = {
                            'text': text,
                            'confidence': int(data['conf'][i]),
                            'bbox': {
                                'x': data['left'][i],
                                'y': data['top'][i],
                                'width': data['width'][i],
                                'height': data['height'][i]
                            },
                            'level': data['level'][i]
                        }
                        
                        threshold = options.get('confidence_threshold', 30)
                        if block['confidence'] >= threshold:
                            blocks.append(block)
                            confidences.append(block['confidence'])
            
            result['blocks'] = blocks
            result['confidence'] = np.mean(confidences) if confidences else 0
            
        except Exception as e:
            result['errors'].append(f"Tesseract error: {str(e)}")
        
        return result
    
    def _ocr_with_easyocr(self, image: Any, options: Dict) -> Dict:
        """Perform OCR using EasyOCR"""
        result = {
            'text': '',
            'blocks': [],
            'confidence': 0.0,
            'errors': []
        }
        
        if not easyocr or not self.reader:
            result['errors'].append("EasyOCR not available")
            return result
        
        try:
            # EasyOCR works with numpy arrays
            if isinstance(image, Image.Image):
                image = np.array(image)
            
            # Perform OCR
            ocr_result = self.reader.readtext(image)
            
            # Process results
            texts = []
            blocks = []
            confidences = []
            
            for (bbox, text, confidence) in ocr_result:
                threshold = options.get('confidence_threshold', 0.3)
                
                if confidence >= threshold:
                    # Convert bbox to standard format
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    
                    block = {
                        'text': text,
                        'confidence': float(confidence) * 100,
                        'bbox': {
                            'x': int(min(x_coords)),
                            'y': int(min(y_coords)),
                            'width': int(max(x_coords) - min(x_coords)),
                            'height': int(max(y_coords) - min(y_coords))
                        }
                    }
                    
                    blocks.append(block)
                    texts.append(text)
                    confidences.append(confidence)
            
            result['text'] = ' '.join(texts)
            result['blocks'] = blocks
            result['confidence'] = np.mean(confidences) * 100 if confidences else 0
            
        except Exception as e:
            result['errors'].append(f"EasyOCR error: {str(e)}")
        
        return result
    
    def _detect_layout(self, image: Any) -> Dict:
        """Detect document layout structure"""
        layout = {
            'regions': [],
            'columns': 0,
            'orientation': 'portrait'
        }
        
        if not cv2:
            return layout
        
        try:
            # Convert to numpy array if needed
            if isinstance(image, Image.Image):
                image = np.array(image)
            
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image
            
            # Detect orientation
            h, w = gray.shape[:2]
            layout['orientation'] = 'landscape' if w > h else 'portrait'
            
            # Simple column detection using vertical projection
            binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            vertical_proj = np.sum(binary, axis=0)
            
            # Find gaps in projection (potential column separators)
            threshold = np.mean(vertical_proj) * 0.5
            gaps = []
            in_gap = False
            gap_start = 0
            
            for i, val in enumerate(vertical_proj):
                if val < threshold and not in_gap:
                    in_gap = True
                    gap_start = i
                elif val >= threshold and in_gap:
                    in_gap = False
                    if i - gap_start > w * 0.05:  # Significant gap
                        gaps.append((gap_start, i))
            
            layout['columns'] = len(gaps) + 1 if gaps else 1
            
            # Detect text regions using morphological operations
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 3))
            dilated = cv2.dilate(binary, kernel, iterations=1)
            
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h
                
                # Filter small regions
                if area > 1000:
                    layout['regions'].append({
                        'type': 'text',
                        'bbox': {'x': x, 'y': y, 'width': w, 'height': h},
                        'area': area
                    })
            
        except Exception as e:
            pass
        
        return layout
    
    def extract_tables(self, image_path: str) -> List[Dict]:
        """Extract tables from document image"""
        tables = []
        
        if not cv2:
            return tables
        
        try:
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect horizontal and vertical lines
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
            
            horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
            vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
            
            # Combine lines
            table_mask = cv2.add(horizontal_lines, vertical_lines)
            
            # Find contours (potential tables)
            contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter by size
                if w > 100 and h > 100:
                    tables.append({
                        'bbox': {'x': x, 'y': y, 'width': w, 'height': h},
                        'confidence': 0.8
                    })
        
        except Exception as e:
            pass
        
        return tables
    
    def batch_process(self, file_paths: List[str], options: Optional[Dict] = None) -> List[Dict]:
        """Process multiple document images"""
        results = []
        
        for file_path in file_paths:
            result = self.process_document(file_path, options)
            result['file'] = file_path
            results.append(result)
        
        return results
    
    def enhance_image_quality(self, image_path: str, output_path: str) -> bool:
        """Enhance image quality for better OCR"""
        if not cv2:
            return False
        
        try:
            image = cv2.imread(image_path)
            
            # Upscale if image is small
            h, w = image.shape[:2]
            if w < 1000:
                scale = 1500 / w
                new_w = int(w * scale)
                new_h = int(h * scale)
                image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            
            # Denoise
            image = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
            
            # Sharpen
            kernel = np.array([[-1,-1,-1],
                              [-1, 9,-1],
                              [-1,-1,-1]])
            image = cv2.filter2D(image, -1, kernel)
            
            cv2.imwrite(output_path, image)
            return True
            
        except Exception as e:
            return False


if __name__ == "__main__":
    # Example usage
    import sys
    
    agent = DocumentOCRAgent(ocr_engine='auto')
    
    if agent.ocr_engine:
        print(f"OCR Engine: {agent.ocr_engine}")
        
        if len(sys.argv) > 1:
            image_path = sys.argv[1]
            
            options = {
                'preprocess': True,
                'enhance_contrast': True,
                'confidence_threshold': 50,
                'detect_layout': True
            }
            
            result = agent.process_document(image_path, options)
            
            print(f"\nProcessing: {image_path}")
            print(f"Extracted text ({len(result['text'])} characters):")
            print(result['text'][:500] + "..." if len(result['text']) > 500 else result['text'])
            print(f"\nConfidence: {result['confidence']:.2f}%")
            print(f"Text blocks found: {len(result['blocks'])}")
            
            if 'layout' in result:
                print(f"Layout: {result['layout']['columns']} column(s), {result['layout']['orientation']}")
            
            if result['errors']:
                print(f"Errors: {result['errors']}")
    else:
        print("No OCR engine available. Install pytesseract or easyocr.")