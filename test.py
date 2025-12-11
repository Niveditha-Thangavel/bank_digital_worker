import json


with open("decisions.json") as f:
    data = json.load(f)
dec =[]
for i in data:
    d = {"customer_id":i["customer_id"],"decision":i["decision"],"Reason":i["reason"]}
    dec.append(d)
print(dec)
