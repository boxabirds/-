import os
import fitz  # PyMuPDF
import argparse
import xml.etree.ElementTree as ET
import cairosvg

def rasterize_svg_to_png(svg_path, png_path, default_width=1920, default_height=1080):
    """
    Converts an SVG file to a PNG file
    Default dimensions are the same ratio as an A4 page (portrait).

    """

    # Parse the SVG file content
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Ensure the SVG has defined width and height
    if 'width' not in root.attrib or 'height' not in root.attrib:
        root.set('width', f"{default_width}px")
        root.set('height', f"{default_height}px")

        # Convert the modified SVG tree back to a string
        svg_content = ET.tostring(root, encoding='utf-8', method='xml')
    else:
        # If width and height are present, read the file content as is
        with open(svg_path, 'rb') as svg_file:
            svg_content = svg_file.read()

    # Convert the SVG (with definite dimensions) to PNG
    cairosvg.svg2png(bytestring=svg_content, write_to=png_path)

def strip_text_from_svg(svg_content):
    """
    Attempts to create image-only svg by stripping <use> elements with 'data-text' attribute sitting
    directly under <svg> or <svg><g> where there's only one <g> tag in the svg doc.
    e.g. <use data-text="H"…>

    Parameters:
    - svg_content (str): A string containing the SVG content to have its text stripped.

    Returns:
    - str: The stripped SVG content as a string.
    """

    # Register namespaces to preserve structure and prefixes
    ET.register_namespace('', "http://www.w3.org/2000/svg")
    ET.register_namespace('xlink', "http://www.w3.org/1999/xlink")

    # Parse the SVG content
    root = ET.fromstring(svg_content)

    # Check if there's only one <g> tag directly under the <svg> root
    g_tags = [child for child in root if child.tag == '{http://www.w3.org/2000/svg}g']
    if len(g_tags) == 1:
        # Use the single <g> tag as the new root
        root = g_tags[0]

    # Iterate over a copy of the root's children
    for child in list(root):
        # Check if the child is a <use> element with a 'data-text' attribute
        if child.tag == '{http://www.w3.org/2000/svg}use' and 'data-text' in child.attrib:
            # Remove the child from the root
            root.remove(child)

    # Return the modified SVG content as a string
    # If the root was changed to a <g> tag, wrap the output in an <svg> tag to ensure validity
    if root.tag == '{http://www.w3.org/2000/svg}g':
        return '<svg xmlns="http://www.w3.org/2000/svg">' + ET.tostring(root, encoding='unicode', method='xml') + '</svg>'
    else:
        return ET.tostring(root, encoding='unicode', method='xml')

def extract_pdf_pymupdf(pdf_path, output_dir, output_type="text"):
    """
    Extracts content from a PDF file using PyMuPDF (fitz) and saves it to the specified directory.
    Supports extracting plain text and images or converting pages to SVG and then rasterizing to PNG.

    Parameters:
    - pdf_path (str): The file path of the input PDF.
    - output_dir (str): The directory path where the extracted content should be saved.
    - output_type (str, optional): The type of output to extract ('text' or 'svg'). Defaults to 'text'.
    """

    doc = fitz.open(pdf_path)

    for page in doc:
        if output_type == "text":
            # Extract and save text and images as before
            text = page.get_text()
            text_path = os.path.join(output_dir, f"page{page.number}_text.txt")
            with open(text_path, "w") as text_file:
                text_file.write(text)

            images = page.get_images(full=True)
            for img_index, img in enumerate(images):
                xref = img[0]
                image = doc.extract_image(xref)
                image_bytes = image["image"]
                img_path = os.path.join(output_dir, f"page{page.number}-image{xref}.png")
                with open(img_path, "wb") as img_file:
                    img_file.write(image_bytes)
        elif output_type == "svg":
            # Generate and save SVG for each page
            svg = page.get_svg_image(matrix=fitz.Identity)
            filtered_svg = strip_text_from_svg(svg)
            svg_path = os.path.join(output_dir, f"page{page.number}.svg")
            with open(svg_path, "w") as svg_file:
                svg_file.write(filtered_svg)
            
            # Rasterize the filtered SVG into PNG
            png_path = os.path.join(output_dir, f"page{page.number}.png")
            rasterize_svg_to_png(svg_path, png_path)

def get_output_dir(source_dir, output_type="text"):
    """
    Determines the output directory based on the source directory and the specified output type.

    Parameters:
    - source_dir (str): The base directory where the source files are located.
    - output_type (str, optional): The type of output ('text' or 'svg') to determine the subdirectory. Defaults to 'text'.

    Returns:
    - str or None: The path to the output directory, or None if the output type is unsupported.
    """

    if output_type == "text":
        return os.path.join(source_dir, "extracted-text")
    elif output_type == "svg":
        return os.path.join(source_dir, "extracted-svg")
    else:
        print(f"Unsupported type: {output_type}")
        return None

def process_pdfs(source_dir, output_type="text", limit=None):
    """
    Processes PDF files from a source directory, extracting content as specified by the output type.
    Can optionally limit the number of processed files.

    Parameters:
    - source_dir (str): The directory containing the PDF files to be processed.
    - output_type (str, optional): The type of content to extract from the PDFs ('text' or 'svg'). Defaults to 'text'.
    - limit (int, optional): The maximum number of PDF files to process. If None, all PDFs in the source directory are processed.
    """

    extracted_dir = get_output_dir(source_dir, output_type)
    if extracted_dir is None:
        return

    os.makedirs(extracted_dir, exist_ok=True)
    pdfs = [f for f in os.listdir(source_dir) if f.endswith(".pdf")]
    if limit:
        pdfs = pdfs[:limit]

    for pdf_name in pdfs:
        arxiv_id = os.path.splitext(pdf_name)[0]
        output_dir = os.path.join(extracted_dir, arxiv_id)
        os.makedirs(output_dir, exist_ok=True)
        pdf_path = os.path.join(source_dir, pdf_name)
        extract_pdf_pymupdf(pdf_path, output_dir, output_type)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--output-type", default="text", help="Specify output type: 'text' or 'svg'.")
    parser.add_argument("-s", "--source", default="cs_CL-cs_AI", help="Specify the source directory containing PDF files.")
    parser.add_argument("-l", "--limit", type=int, help="Limit the number of processed PDF files.")

    args = parser.parse_args()
    process_pdfs(args.source, args.output_type, args.limit)
