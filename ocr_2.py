def group_horizontal_lines_robust(raw_results, y_tol_factor=0.5, x_gap_factor=2.0):
    processed_boxes = []
    
    # 1. Calculate the average height of the bounding boxes to use as a dynamic baseline
    total_height = 0
    for bbox, text, prob in raw_results:
        box_height = bbox[2][1] - bbox[0][1]
        total_height += box_height
        
        y_center = (bbox[0][1] + bbox[2][1]) / 2
        x_min = bbox[0][0]
        x_max = bbox[1][0]
        processed_boxes.append({
            'text': text, 
            'y_center': y_center, 
            'x_min': x_min, 
            'x_max': x_max
        })
        
    avg_height = total_height / len(raw_results)
    
    # 2. Set dynamic tolerances based on the actual text size in the image
    y_tolerance = avg_height * y_tol_factor
    max_x_gap = avg_height * x_gap_factor
    
    # 3. Sort top-to-bottom
    processed_boxes.sort(key=lambda box: box['y_center'])
    
    lines = []
    current_line = []
    current_y = None
    
    # 4. Cluster using the dynamic y_tolerance
    for box in processed_boxes:
        if current_y is None:
            current_line.append(box)
            current_y = box['y_center']
        elif abs(box['y_center'] - current_y) <= y_tolerance:
            current_line.append(box)
            current_y = sum(b['y_center'] for b in current_line) / len(current_line)
        else:
            current_line.sort(key=lambda b: b['x_min'])
            formatted_line = current_line[0]['text']
            
            # 5. Detect columns using the dynamic max_x_gap
            for i in range(1, len(current_line)):
                gap = current_line[i]['x_min'] - current_line[i-1]['x_max']
                if gap > max_x_gap:
                    formatted_line += f"\n{current_line[i]['text']}"
                else:
                    formatted_line += f" {current_line[i]['text']}"
            
            lines.append(formatted_line)
            current_line = [box]
            current_y = box['y_center']
            
    # Process the final line
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

# Execute with the dynamic factors (adjust factors slightly if needed, rather than raw pixels)
final_robust_text = group_horizontal_lines_robust(raw_results, y_tol_factor=0.6, x_gap_factor=1.8)

print("--- Final Robust Multi-Column Extraction ---")
for line in final_robust_text:
    print(line)
