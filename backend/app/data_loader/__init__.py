from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from typing import Optional


class DataIngestion:
    def __init__(self, url: Optional[str] = None, csv_file: Optional[str] = None):
        self.url = url
        self.csv_file = csv_file

    def process_web(self):
        docs = [WebBaseLoader(self.url).load()]
        return docs

    def process_csv(self):
        loader = CSVLoader(file_path=self.csv_file, encoding="utf-8")
        data = loader.load()
        return data
