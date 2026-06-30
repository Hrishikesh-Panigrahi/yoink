from PIL import Image, ImageDraw
import os
import math

def create_icon():
    # Create a 512x512 image with transparency
    size = 512
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Draw a circular background
    margin = 20
    draw.ellipse([margin, margin, size-margin, size-margin], 
                 fill='#3498db')
    
    # Draw the torrent symbol (three arrows in a circle)
    center = size // 2
    radius = size // 3
    
    # Draw three arrows
    for i in range(3):
        angle = i * 120  # 120 degrees between each arrow
        # Convert angle to radians
        rad = angle * 3.14159 / 180
        
        # Calculate arrow position
        x = center + int(radius * 0.7 * math.cos(rad))
        y = center + int(radius * 0.7 * math.sin(rad))
        
        # Draw arrow
        arrow_size = radius // 3
        draw.polygon([
            (x, y - arrow_size),  # Top
            (x - arrow_size, y + arrow_size),  # Bottom left
            (x + arrow_size, y + arrow_size),  # Bottom right
        ], fill='white')
    
    # Save the icon
    icon_path = os.path.join(os.path.dirname(__file__), 'app_icon.png')
    image.save(icon_path)
    return icon_path

if __name__ == '__main__':
    create_icon() 