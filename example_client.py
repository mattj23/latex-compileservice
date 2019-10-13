import requests 
import os 
import json 

uploads = ["test.tex", "test2.tex", "logo.png"]

handles = {}

for upload in uploads:
    handles[upload] = open(os.path.join("test_assets", upload), 'rb')

handles["compiler"] = (None, "xelatex")
handles["target"] = (None, "test.tex")

rq = requests.post('http://localhost:5000/api/1.0/session', files=handles)
print(rq)
print(rq.json())

for k, v in handles.items():
    try:
        v.close()
    except:
        pass