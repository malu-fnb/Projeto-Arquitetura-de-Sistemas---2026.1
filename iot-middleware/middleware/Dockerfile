FROM python

WORKDIR /middleware

RUN apt update  && apt install -y git

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

#CMD ["python", "src/main.py"]