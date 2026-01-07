**Authors: Group 4**
# Computational Creativy: Assignment COCONUT

## Overview
This project implements a interactive co-creative system that generates a scrapbook page for a travel journal based on the input images and a text file describing the trip. The scrapbook generator is based on an evolutionary algorithm where the user chooses which generated offspring is selected for the parent population for the next generation. The final generation contains the desired scrapbook pages. The generation is done with OpenAI's image generation model gpt-image-1-mini. This repository contains the python file ``cc_final_assignment.py``. This repository requires an input directory, for example, ``\france``, only containing ``jpg`` or ``png`` - and ``txt``-files . After running, the output of each generation is found in the directory ``\results``.


## System requirements
* **Programming language:** Python 3.10 or higher
* **Required packages:**
    * ``openai``
    * ``Pillow``
    * ``tqdm``
    * ``json`` (standard library)
    * ``base64`` (standard library)
    * ``pathlib`` (standard library)
    * ``io`` (standard library)
    * ``random`` (standard library)

## How to run
1) Download this repository.

2) Navigate to the project directory in your terminal.

3) Run: ``python3 cc_final_assignment.py your-api-key``
