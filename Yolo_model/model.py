from ultralytics import YOLO
import cv2
# Load YOLO model 
model = YOLO('yolov8n.pt')

# import video
video_source = r'Yolo_model/vid.mp4'

# Can use streaming video from IP camera by RSTP protocol
# video_source = 'rtsp://your_camera_ip/stream'

cap = cv2.VideoCapture(video_source)
if not cap.isOpened():
    print("Unable to open video!")
else:
    print("Open video successfully!")

counts = {} # Initialize counts dictionary for vehicle types globally to avoid reinitializing it in every frame
while cap.isOpened():
    ret, frame = cap.read()
    # if frame is None then break:
    if not ret:
        break

    # Inference
    results = model(frame)

    # print the counts of detected objects
    for box in results[0].boxes.data:
        confidence = box[4]  # Confidence score
        if confidence < 0.3:  # Lower the threshold (default is often 0.5)
            continue
        
        class_id = int(box[5])
        label = model.names[class_id]
        
        if label in ['car', 'bus', 'truck', 'motorcycle', 'bicycle']:
            counts[label] = counts.get(label, 0) + 1 # recount the number of vehicles
            # continue counting the number of vehicles
            # if label not in counts:
            #     counts[label] = 1
            # else:
            #     counts[label]+=1

    print("Detected:", counts)

    # draw bounding boxes and labels on the frame
    annotated_frame = results[0].plot()

    # resize frame to display in a smaller window
    annotated_frame = cv2.resize(annotated_frame, (800, 600))

    # show the annotated frame
    cv2.imshow('Traffic Monitoring', annotated_frame)

    if cv2.waitKey(1) == 27:  # press 'Esc' to exit
        break

cv2.destroyAllWindows()
