#!/usr/bin/env python3
import os
import argparse
import cv2
import re
import time
import glob

def natural_sort_key(s):
    """
    Sort strings containing numbers in natural order.
    """
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]

def play_image_sequence(folder_path, fps=5, loop=False):
    """
    Display a sequence of images from a folder as a video.
    
    Args:
        folder_path: Path to the folder containing PNG images
        fps: Frames per second for playback
        loop: Whether to loop the playback
    """
    # Get all PNG files and sort them
    image_files = glob.glob(os.path.join(folder_path, "*.png"))
    if not image_files:
        print(f"No PNG images found in {folder_path}")
        return
        
    image_files.sort(key=natural_sort_key)
    print(f"Found {len(image_files)} images to play")
    
    # Calculate frame delay in milliseconds
    frame_delay = int(1000 / fps)
    
    # Create a window
    cv2.namedWindow("Image Sequence", cv2.WINDOW_NORMAL)
    
    # Read the first image to get dimensions
    first_image = cv2.imread(image_files[0])
    if first_image is None:
        print(f"Error: Could not read {image_files[0]}")
        return
        
    height, width = first_image.shape[:2]
    # Resize the window if image is too large
    if width > 1200 or height > 800:
        cv2.resizeWindow("Image Sequence", min(width, 1200), min(height, 800))
    
    print(f"Playback started at {fps} FPS. Press 'q' to quit, 'p' to pause/resume.")
    print(f"Use '+'/'-' to adjust speed, 'r' to restart.")
    
    index = 0
    running = True
    paused = False
    
    while running:
        if not paused:
            # Read current image
            current_file = image_files[index]
            image = cv2.imread(current_file)
            
            if image is not None:
                # Show image with filename
                filename = os.path.basename(current_file)
                cv2.putText(image, filename, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                            1, (0, 255, 0), 2)
                cv2.imshow("Image Sequence", image)
                
                # Move to next image
                index = (index + 1) % len(image_files)
                
                # If reached the end and not looping, stop
                if index == 0 and not loop:
                    print("End of sequence reached")
                    if not loop:
                        # Pause at the end if not looping
                        paused = True
            else:
                print(f"Error reading {current_file}")
                index = (index + 1) % len(image_files)
        
        # Check for key presses (wait for frame_delay ms)
        key = cv2.waitKey(frame_delay)
        if key != -1:
            key = key & 0xFF  # Extract the lower byte
            
            if key == ord('q'):
                running = False
            elif key == ord('p'):
                paused = not paused
                print("Playback", "paused" if paused else "resumed")
            elif key == ord('+') or key == ord('='):
                fps = min(fps + 1, 30)
                frame_delay = int(1000 / fps)
                print(f"Speed increased to {fps} FPS")
            elif key == ord('-'):
                fps = max(fps - 1, 1)
                frame_delay = int(1000 / fps)
                print(f"Speed decreased to {fps} FPS")
            elif key == ord('r'):
                index = 0
                print("Playback restarted")
    
    cv2.destroyAllWindows()
    print("Playback ended")

def main():
    parser = argparse.ArgumentParser(description='Play a sequence of images as a video')
    parser.add_argument('--folder', type=str, default='./Bounding_Boxed',
                        help='Path to the folder containing images (default: ./Bounding_Boxed)')
    parser.add_argument('--fps', type=int, default=5,
                        help='Frames per second (default: 5)')
    parser.add_argument('--loop', action='store_true',
                        help='Loop the playback')
    args = parser.parse_args()
    
    play_image_sequence(args.folder, args.fps, args.loop)

if __name__ == "__main__":
    main()