# Install required libraries (run this if you haven't already)
!pip install easyocr docling opencv-python-headless matplotlib

import easyocr
import cv2
import matplotlib.pyplot as plt
import numpy as np
from docling.datamodel.pipeline_options import PipelineOptions, EasyOcrOptions
from docling.document_converter import DocumentConverter, ImageFormatOption
from docling.datamodel.base_models import InputFormat


---------------------------------------

# Initialize EasyOCR with German ('de')
reader = easyocr.Reader(['de'], gpu=False) # Set gpu=False if running locally without CUDA

# Read the image and extract data
image_path = "docs/images.png"
raw_results = reader.readtext(image_path)

# Print raw, unsorted results
for bbox, text, prob in raw_results:
    print(f"Text: {text} | Confidence: {prob:.2f}")

    ---------------------------------

    # Load image with OpenCV
img = cv2.imread(image_path)
img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# Draw bounding boxes
for bbox, text, prob in raw_results:
    # bbox is a list of 4 points: [top-left, top-right, bottom-right, bottom-left]
    pt1 = (int(bbox[0][0]), int(bbox[0][1]))
    pt2 = (int(bbox[2][0]), int(bbox[2][1]))
    cv2.rectangle(img, pt1, pt2, (0, 255, 0), 2)
    cv2.putText(img, text, (pt1[0], pt1[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

# Display the image
plt.figure(figsize=(10, 6))
plt.imshow(img)
plt.axis('off')
plt.title("EasyOCR Default Bounding Boxes")
plt.show()

--------------------------------------------

# Custom sorting logic: Sort top-to-bottom, but group items on the same horizontal line
# by their X-coordinate (left-to-right)
def custom_sort(result_list, y_tolerance=15):
    # Sort primarily by Y (top of the bounding box), then by X (left of the bounding box)
    return sorted(result_list, key=lambda r: (r[0][0][1] // y_tolerance, r[0][0][0]))

sorted_results = custom_sort(raw_results)

print("--- Custom Sorted Extraction ---")
for bbox, text, prob in sorted_results:
    print(text)

-------------------------------------------- 
def group_horizontal_lines_with_columns(raw_results, y_tolerance=12, max_x_gap=45):
    processed_boxes = []
    
    # 1. Calculate Y-center, Left X, and Right X for every box
    for bbox, text, prob in raw_results:
        y_center = (bbox[0][1] + bbox[2][1]) / 2
        x_min = bbox[0][0]
        x_max = bbox[1][0] # The right-side edge of the bounding box
        processed_boxes.append({
            'text': text, 
            'y_center': y_center, 
            'x_min': x_min, 
            'x_max': x_max
        })
    
    # 2. Sort top-to-bottom
    processed_boxes.sort(key=lambda box: box['y_center'])
    
    lines = []
    current_line = []
    current_y = None
    
    # 3. Cluster boxes by Y-axis
    for box in processed_boxes:
        if current_y is None:
            current_line.append(box)
            current_y = box['y_center']
        elif abs(box['y_center'] - current_y) <= y_tolerance:
            current_line.append(box)
            current_y = sum(b['y_center'] for b in current_line) / len(current_line)
        else:
            # 4. Process the completed line for X-axis gaps (Columns)
            current_line.sort(key=lambda b: b['x_min'])
            
            formatted_line = current_line[0]['text']
            for i in range(1, len(current_line)):
                # Calculate the horizontal space between the current box and the previous box
                gap = current_line[i]['x_min'] - current_line[i-1]['x_max']
                
                if gap > max_x_gap:
                    # If the gap is large, treat it as a new column and push it to a new line
                    formatted_line += f"\n{current_line[i]['text']}"
                else:
                    # If the gap is small, it's just a space between words in the same field
                    formatted_line += f" {current_line[i]['text']}"
            
            lines.append(formatted_line)
            
            # Start the next line
            current_line = [box]
            current_y = box['y_center']
            
    # Process the very last line in the document
    if current_line:
        current_line.sort(key=lambda b: b['x_min'])
        formatted_line = current_line[0]['text']
        for i in range(1, len(current_line)):
            gap = current_line[i]['x_min'] - current_line[i-1]['x_max']
            if gap > max_x_gap:
                formatted_line += f"\n{current_line[i]['text']}"
            else:
                formatted_line += f" {current_line[i]['text']}"
        lines.append(formatted_line)
        
    return lines

# Execute the new column-aware grouper
final_column_text = group_horizontal_lines_with_columns(raw_results, y_tolerance=12, max_x_gap=45)

print("--- Final Multi-Column Extraction ---")
for line in final_column_text:
    print(line)