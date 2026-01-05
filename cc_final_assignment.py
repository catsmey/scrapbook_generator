from openai import OpenAI
import json
import base64
import pathlib
import io
from PIL import Image
import random

scrapbook_styles = ["normal","vintage", "nature", "whimsical", "cute/kawaii", "futuristic", "maximalist", "gothic", "pop art"]
        
def generate_initial_population(client, text, images, analysis, n, styles):
    out_dir = pathlib.Path("results") / "generation0"
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n):
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

        if image_data:
            image_base64 = image_data[0]
            out_path = out_dir / f"scrapbook{i+1}.png"
            with out_path.open("wb") as f:
                f.write(base64.b64decode(image_base64))
            Image.open(io.BytesIO(base64.b64decode(image_base64))).show()

# def generate_initial_population(client, text, images, analysis, n, styles):
#     out_dir = pathlib.Path("results") / "generation0"
#     out_dir.mkdir(parents=True, exist_ok=True)
#     for i in range(n):
#         style = styles[i]
#         print(f"Generating scrapbook in {style} style...")
#         design_prompt = f"""
#         Design a high-resolution travel journal scrapbook page as an image.
#         Include the attached photos and add elements such as paper textures, fabrics, ribbons, natural elements like leaves and flowers, tape, hand-drawn accents, short texts describing the experience (not the input text), collected travel items like postcards or maps, stickers, and more typical scrapbook elements. 
#         Play with layering papers, photographs, and embellishments.
#         Create the scrapbook in a {style} scrapbook style.
#         Use this trip summary, the extracted analysis and the attached photos to guide composition:

#         Trip summary:
#         {text}

#         Analysis:
#         {json.dumps(analysis, ensure_ascii=False)}

#         """
#         result = client.images.edit(
#             model="gpt-image-1.5",
#             image=[open(p, "rb") for p in images],
#             prompt=design_prompt,
#             n=1,
#         )

#         img_bytes = base64.b64decode(result.data[0].b64_json)
#         out_path = out_dir / f"scrapbook{i+1}.png"
#         with out_path.open("wb") as f:
#             f.write(img_bytes)
#         Image.open(io.BytesIO(img_bytes)).show()

def encode_images(image_paths):
    image_urls = []
    for p in image_paths:
        with open(p, "rb") as image_file:
            data = base64.b64encode(image_file.read()).decode("utf-8")
        tag = "image/jpeg" if p.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
        image_urls.append(f"data:{tag};base64,{data}")
    return image_urls

def downscale_images(image_paths):
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

def analyze_emotions_and_info(client, text, image_urls):
    analysis_prompt = """
You are a travel-journal emotion and content analyst.
Given the user’s travel text and photos, extract structured information to guide scrapbook design.

Return STRICT JSON ONLY with this schema:
{
  "emotions_overall": ["joy|serenity|awe|nostalgia|..."],
  "sentiment": "positive|neutral|negative",
  "key_locations": [str],
  "key_events": [str],
  "color_palette": [{"hex": "#RRGGBB"}],
  "season": [str]
}

Constraints:
- Make color palette align with emotions and imagery.
- JSON only. No markdown. No extra commentary.
"""
    user_content = [{"type": "input_text", "text": text}]
    for url in image_urls:
        user_content.append({"type": "input_image", "image_url": url})
    result = client.responses.create(
        model="gpt-5.1",
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": analysis_prompt}]},
            {"role": "user", "content": user_content},
        ],
    )
    #print(result.output_text)
    answer = result.output_text
    try:
        analysis = json.loads(answer)
    except json.JSONDecodeError:
        print("Error exptracting information. Try again.")  
    return analysis

def crossover():
    prompt = """
    Combine the two provided scrapbooks to create a new design. Do not modify the original photos."""
    return prompt

def mutation():
    #2 types of mutation: style change or composition change 0.5 probability each
    if random.random() < 0.5:
        style = random.choice(scrapbook_styles)
        prompt = f"""
        Modify the provided scrapbook by changing its style to {style}. Do not modify the original photos."""
    else:
        prompt = """
        Modify the provided scrapbook by changing composition/arrangement of the elements. Do not change any of the individual components."""
    return prompt

def evolutionairy_algorithm(client, history, n, num_generations):
    mutation_rate = 0.7
    crossover_rate = 0.7
    # pick n random styles for initial population
    styles = random.sample(scrapbook_styles, n)
    #generate_initial_population(client, text, images, analysis, n, styles)
    
    for generation in range(0, num_generations):
        print(f"Generation {generation} completed. Please select the two best designs from the 'results/generation{generation}' folder and enter their numbers separated by commas. To improve them further.")
        selected = input("Enter favorite scrapbooks: ").split(",")
        # retrieve the images from results/generation{generation} to use as parents
        parent_images = []
        for s in selected:
            parent_path = pathlib.Path("results") / f"generation{generation}" / f"scrapbook{int(s)}.png"
            parent_images.append(parent_path)
        parent_urls = encode_images(parent_images)
        # create next generation
        out_dir = pathlib.Path("results") / f"generation{generation+1}"
        out_dir.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            if random.random() < crossover_rate:
                # crossover: mix elements from both parents
                prompt = crossover() 
                user_content = []
                for url in parent_urls:
                    user_content.append({"type": "input_image", "image_url": url})
            else:
                # mutation: 1. change style 2. change composition
                if random.random() < mutation_rate:
                    parent = random.choice(parent_urls)
                    prompt = mutation()
                    user_content = [{"type": "input_image", "image_url": parent}]
                # original parent is kept
                else:
                    # save parent image as is to next generation
                    parent = random.choice(parent_images)
                    out_path = out_dir / f"scrapbook{i+1}.png"
                    with parent.open("rb") as source, out_path.open("wb") as destination:
                        destination.write(source.read())
                    continue
                
            messages = history + [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": prompt}],
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ]   
            resp = client.responses.create(
                model="gpt-5.1",
                input=messages,
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

def create_history(text, image_urls):
    # gives the model some context to its goal
    base_prompt = """You are a travel scrapbook designer. 
    You create scrapbook pages as images about a user's travel experience based on provided photos and a description of the trip. 
    You add typical scrapbook elements such as paper textures, fabrics, ribbons, natural elements like leaves and flowers, tape, hand-drawn accents, short texts describing the experience (not the input text), collected travel items like postcards or maps, stickers, and more typical scrapbook elements.
    You play with layering papers, photographs, and embellishments.
    Only create scrapbook pages that keep the original trip photos and story as the core content.
    """
    history = [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": base_prompt}],
        },
        {
            "role": "user",
            "content": (
                [{"type": "input_text", "text": text}]
                + [{"type": "input_image", "image_url": u} for u in image_urls]
            ),
        },
    ]
    return history

if __name__ == "__main__": 
    client = OpenAI()   
    text, images = get_initial_user_input()
    downscale_images(images)
    image_urls = encode_images(images)
    #analysis = analyze_emotions_and_info(client, text, image_urls)
    analysis= {}
    history = create_history(text, image_urls)
    evolutionairy_algorithm(client, history, n=4, num_generations=3)

    
    
