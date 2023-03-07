import requests
import random # only used to generate example data

# credentials for belfast.pvos.org (for this particular sensor feed)
public_key = "[YOUR PUBLIC KEY]"  
private_key = "[YOUR PRIVATE KEY]"

# these will stay fixed:
base_url = "http://bayou.pvos.org/data/"
full_url = base_url+public_key

# example data (NOTE: 'node_id' is a required parameter, can be any integer, typically equal to zero)
co2_ppm = random.randint(500,550)
node_id=0 

# the JSON object we'll be POST-ing to 'full_url' ...
# NOTE: we must include the private_key as one of the parameters;
# and 'distance_meters' is one of several possible parameters in the postgres database.
myobj = {"private_key":private_key, "co2_ppm":co2_ppm,"node_id":node_id}

x = requests.post(full_url, data = myobj)
print (co2_ppm)
print(x.text)
