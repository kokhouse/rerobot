FROM python:3
ADD requirements.txt /requirements.txt
RUN pip install --upgrade -r requirements.txt
ADD . /
CMD ["python", "run_bot.py"]