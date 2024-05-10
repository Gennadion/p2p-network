FROM python:3.10

WORKDIR /



COPY requirements.txt .

RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

# Create a directory for shared files
RUN mkdir /shared

EXPOSE 8000


CMD ["python3", "p2pUI/manage.py", "runserver", "0.0.0.0:8000"]
