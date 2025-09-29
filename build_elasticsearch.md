# Notes for building your elasticsearch server via docker 
# i am for now using an older version of es so i installed an older python client

> pip install elasticsearch==8.6.2 

> docker pull docker.elastic.co/elasticsearch/elasticsearch:8.6.1

> docker run -d \
--name es-node01 \
-p 9200:9200 \
-e "discovery.type=single-node" \
-e "xpack.security.enabled=false" \
docker.elastic.co/elasticsearch/elasticsearch:8.6.1


# now you should be seing a container named es-node01 running on localhost:9200 

# then run the file named elastic_index to create the index for our project 

# to check if it is created correctly run 

> curl http://localhost:9200/_cat/indices

# you should be seing something like 

- yellow open parliament_speeches dy0B9BIUQqmHqdF4sc2uyA 1 1 0 0 225b 225b


# after bulking the docs (which elastic_index.py does already) you will see the speech objects at 

> http://localhost:9200/parliament_speeches/_search?pretty&q=*


