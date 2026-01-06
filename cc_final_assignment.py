from openai import OpenAI
import json
import base64
import pathlib
import io
from PIL import Image
import random
from tqdm import tqdm

scrapbook_styles = ["normal","vintage", "nature", "whimsical", "cute/kawaii", "futuristic", "maximalist", "gothic", "pop art"]
        
def generate_initial_population(client, text, image_urls, n, styles):
    out_dir = pathlib.Path("results") / "generation0"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    for i in tqdm(range(n), desc="Generating initial population", unit="scrapbook"):
        style = styles[i]
        print(f"Generating scrapbook in {style} style...")
        design_prompt = f"""
        Design a travel journal scrapbook page as an image.
        Include the attached photos and add elements such as paper textures, fabrics, ribbons, natural elements like leaves and flowers, tape, hand-drawn accents, short texts describing the experience (not the input text), collected travel items like postcards or maps, stickers, and more typical scrapbook elements. 
        Play with layering papers, photographs, and embellishments.
        Create the scrapbook in a {style} scrapbook style.
        Use this trip summary and the attached photos to guide composition:
        """
        user_content = [{"type": "input_text", "text": text}]
        for url in image_urls:
            user_content.append({"type": "input_image", "image_url": url})
        resp = client.responses.create(
            model="gpt-5.1",
            input=[
                    {"role": "system", "content": [{"type": "input_text", "text": design_prompt}]},
                    {"role": "user", "content": user_content},
                ],
            tools=[{"type": "image_generation", "model": "gpt-image-1-mini"}], #, "input_fidelity": "high"
        )
        
        image_data = [
            output.result
            for output in resp.output
            if output.type == "image_generation_call"
        ]

        # save and show image
        if image_data:
            image_base64 = image_data[0]
            out_path = out_dir / f"scrapbook{i+1}.png"
            with out_path.open("wb") as f:
                f.write(base64.b64decode(image_base64))
            Image.open(io.BytesIO(base64.b64decode(image_base64))).show()

def encode_images(image_paths):
    # encode images to base64 data URLs to send to openai API
    image_urls = []
    for p in image_paths:
        with open(p, "rb") as image_file:
            data = base64.b64encode(image_file.read()).decode("utf-8")
        tag = "image/jpeg" if p.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
        image_urls.append(f"data:{tag};base64,{data}")
    return image_urls

def downscale_images(image_paths):
    # if images are too large they are downscaled to save memory and costs
    for p in image_paths:
        img = Image.open(p)
        # Downscale if larger than max_side.
        w, h = img.size
        max_dim = max(w, h)
        if max_dim > 960:
            scale = 960 / float(max_dim)
            new_size = (int(w * scale), int(h * scale))
            img = img.resize(new_size, Image.LANCZOS)
        img.save(p)

def compare_scrapbooks(parent_urls):
    prompt = """
    You are given two previously generated travel scrapbook designs, both created from the same base prompt.

    Your task is NOT to redesign the page or rewrite the full prompt.
    Instead, carefully analyze both scrapbook designs and extract their strongest shared and complementary visual components.

    Write short, concise instruction lines that can be added to the original prompt to guide the generation of a new scrapbook design that incorporates elements from both designs.
    Do NOT include any instuctions about the contents of the photographs as these must remain unchanged.
    
    Focus on:
    - Layout structure (photo placement, balance, layering)
    - Repeating motifs or embellishments (e.g. tape, frames, icons, pressed plants)
    - Color palette and material textures
    - Typography and caption style
    - Mood and storytelling approach

    Do not repeat or paraphrase the original prompt.
    Do not describe the existing designs.

    Output only a short bullet list of additive instructions, written as prompt-ready imperatives (e.g. “Emphasize…”, “Blend…”, “Incorporate…”).

    The instructions should be general enough to apply to new images, but specific enough to clearly merge the visual DNA of both scrapbook designs.
    """
    user_content = []
    for url in parent_urls:
        user_content.append({"type": "input_image", "image_url": url})
    
    resp = client.responses.create(
                model="gpt-5.1",
                input=[
                    {"role": "system", "content": [{"type": "input_text", "text": prompt}]},
                    {"role": "user", "content": user_content},
                ],
            )
    return resp.output_text
    
def evolutionary_algorithm(client, text, image_urls, n, num_generations):
    mutation_rate = 0.7
    crossover_rate = 0.5
    # pick n random styles for initial population
    styles = random.sample(scrapbook_styles, n)
    generate_initial_population(client, text, image_urls, n, styles)
    
    for generation in range(0, num_generations):
        print(f"Generation {generation} completed. Please select the two best designs from the 'results/generation{generation}' folder and enter their numbers separated by commas. To improve them further.")
        
        # let user select parents
        selected = input("Enter favorite scrapbooks: ").split(",")
        parent_images = []
        for s in selected:
            parent_path = pathlib.Path("results") / f"generation{generation}" / f"scrapbook{int(s)}.png"
            parent_images.append(parent_path)
        parent_urls = encode_images(parent_images)
        
        # create next generation
        out_dir = pathlib.Path("results") / f"generation{generation+1}"
        out_dir.mkdir(parents=True, exist_ok=True)
        added_prompt = compare_scrapbooks(parent_urls)
        for i in tqdm(range(n), desc=f"Generation {generation+1}", unit="scrapbook"):
            user_content = [
                {"type": "input_text", "text": text},
                *[{"type": "input_image", "image_url": u} for u in image_urls],
            ]
            if random.random() < crossover_rate:
                # crossover: mix elements from both parents
                prompt = f"""
                            You are given a trip description and original trip photos (ground truth).
                            Design a travel journal scrapbook page as an image.
                            Include the attached photos and add elements such as paper textures, fabrics, ribbons, natural elements like leaves and flowers, tape, hand-drawn accents, short texts describing the experience (not the input text), collected travel items like postcards or maps, stickers, and more typical scrapbook elements. 
                            Play with layering papers, photographs, and embellishments.
                            Favor richness over simplicity: add layered papers, visible textures, torn edges, and other scrapbook elementsThe result should feel handcrafted, tactile, and densely detailed rather than minimal or flat.
                            Use the trip summary and the attached photos to guide composition.
                            Do NOT redraw, recolor, or reinterpret the photos.
                            Use the following additional instructions to guide your design:
                            
                            {added_prompt}
                            """
            else:
                # mutation: 1. change style 2. change composition
                if random.random() < mutation_rate:
                    parent = random.choice(parent_urls)
                    prompt = mutation()
                    user_content.append({"type": "input_image", "image_url": parent})
                else:
                    # save parent image as is to next generation
                    parent = random.choice(parent_images)
                    out_path = out_dir / f"scrapbook{i+1}.png"
                    with parent.open("rb") as source, out_path.open("wb") as destination:
                        destination.write(source.read())
                    continue
            
            resp = client.responses.create(
                model="gpt-5.1",
                input=[
                    {"role": "system", "content": [{"type": "input_text", "text": prompt}]},
                    {"role": "user", "content": user_content},
                ],
                tools=[{"type": "image_generation", "model": "gpt-image-1-mini"}],
            )
        
            image_data = [
                output.result
                for output in resp.output
                if output.type == "image_generation_call"
            ]

            if image_data:
                image_base64 = image_data[0]
                out_path = out_dir / f"scrapbook{i+1}.png"
                with out_path.open("wb") as f:
                    f.write(base64.b64decode(image_base64))
                Image.open(io.BytesIO(base64.b64decode(image_base64))).show()
       
def mutation():
    #2 types of mutation: style change or composition change 0.5 probability each
    if random.random() < 0.5:
        style = random.choice(scrapbook_styles)
        prompt = f"""
            You are given:
            - The original trip description and original trip photos (ground truth).
            - A scrapbook design created from this trip.

            Your task:
            Modify the scrapbook by changing its decorative style to a "{style}" scrapbook aesthetic.

            How to change the style:
            - Adjust colors, textures, embellishments, and overall visual theme to match the "{style}" style.
            - Add elements such as paper textures, fabrics, ribbons, natural elements like leaves and flowers, tape, hand-drawn accents, short texts describing the experience (not the input text), collected travel items like postcards or maps, stickers, and more typical scrapbook elements. 
            - Replace or restyle decorative elements to fit the new style.
            - Maintain a dense, layered scrapbook feel.

            Do NOT redraw, recolor or reinterpret the photos.
            """

    else:
        prompt = """
        You are given:
        - The original trip description and original trip photos (ground truth).
        - A scrapbook design created from this trip.

        Your task:
        Modify the scrapbook by changing the composition and arrangement of elements.

        How to change the composition:
        - Maintain the same aesthetic style
        - Change the position, angles, and of photos and decorative elements
        - Experiment with different layering, overlaps, depth, spacing, and alignment.
        - Preserve and emphasize small details such as paper edges, textures, and hand-drawn accents.

        Do NOT redraw, recolor, or reinterpret the photos.
        """
    return prompt
    
def get_initial_user_input():
    print("To create a new travel yournal page, please place the desired images (to be included in the scrapbook) and a txt file containing a description of your trip in a folder in the same directory as this script. Please enter the folder name below.")
    input_folder = input("Folder name: ")
    
    # extract text file and images from folder
    folder_path = pathlib.Path(input_folder).expanduser().resolve()
    text_path = next(folder_path.glob("*.txt"))
    
    # read text file
    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()
    image_paths = list(folder_path.glob("*.jpg")) + list(folder_path.glob("*.png"))
    return text, image_paths

if __name__ == "__main__": 
    client = OpenAI()   
    text, images = get_initial_user_input()
    downscale_images(images)
    image_urls = encode_images(images)
    evolutionary_algorithm(client, text, image_urls, n=4, num_generations=3)

    
    
