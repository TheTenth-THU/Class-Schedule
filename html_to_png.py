import os
from html2image import Html2Image

def export_image(html_path, image_path, remote=False):
    # store the image dir
    image_dir = os.path.abspath(os.path.join(image_path, os.pardir))
    image_path = os.path.basename(image_path)

    # check if the png file already exists
    if os.path.exists(os.path.join(image_dir, image_path)):
        os.remove(os.path.join(image_dir, image_path))

    # process the html file
    hti = Html2Image(size=(1080, 1920))
    if not remote:
        hti.screenshot(other_file=html_path, save_as=image_path)
    else:
        hti.screenshot(url=html_path, save_as=image_path)

    # move the image to the correct dir
    os.makedirs(image_dir, exist_ok=True)
    os.rename(image_path, os.path.join(image_dir, image_path))

    image_path = os.path.join(image_dir, image_path)
    return image_path

if __name__ == '__main__':
    html_path = 'demo/schedule.html'
    image_path = 'demo/schedule.png'
    export_image(html_path, image_path)