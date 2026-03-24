import warnings
warnings.filterwarnings("ignore")


from dotenv import load_dotenv
import os

from utils.pdf_reader import read_pdf
from graph_builder import app

load_dotenv()

documents_folder = "documents"

for file in os.listdir(documents_folder):

    if file.endswith(".pdf"):

        file_path = os.path.join(documents_folder, file)

        print("--------------------------------------------------")
        print(f"Processing document: {file}")

        text = read_pdf(file_path)

        result = app.invoke({
            "text": text,
            "document_name": file
        })

        print("Processing complete")