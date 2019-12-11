from multicorn.utils import log_to_postgres, ERROR, WARNING, DEBUG
from neo4j import GraphDatabase, basic_auth, CypherError
import json
import ast
if sys.version_info.major == 3:
    unicode = str
    
"""
Neo4j Postgres function
"""
def cypher(plpy, query, params, url, login, password):
    """
        Make cypher query and return JSON result
    """
    driver = GraphDatabase.driver( url, auth=basic_auth(login, password))
    session = driver.session()
    log_to_postgres("Cypher function with query " + query + " and params " + unicode(params), DEBUG)

    # Execute & retrieve neo4j data
    try:
        for record in session.run(query, ast.literal_eval(params)):
            jsonResult  = "{"
            for key in record.keys():
                if len(jsonResult) > 1:
                    jsonResult += ","
                jsonResult += '"' + key + '":'
                object = record[key]
                if object.__class__.__name__ == "Node":
                    jsonResult += node2json(object)
                elif object.__class__.__name__ == "Relationship":
                    jsonResult += relation2json(object)
                elif object.__class__.__name__ == "Path":
                    jsonResult += path2json(object)
                else:
                    jsonResult += json.dumps(object)
            jsonResult += "}"
            yield jsonResult
    except CypherError:
        raise RuntimeError("Bad cypher query : " + statement)
    finally:
        session.close()

def cypher_with_server(plpy, query, params, server):
    """
        Make cypher query and return JSON result
    """
    sql = "SELECT unnest(srvoptions) AS conf FROM pg_foreign_server"
    if server:
        sql = "SELECT unnest(srvoptions) AS conf FROM pg_foreign_server WHERE srvname='" + server +"'"

    url = 'bolt://localhost'
    login = None
    password = None

    for row in plpy.cursor(sql):
        if row['conf'].startswith("url="):
            url = row['conf'].split("url=")[1]
        if row['conf'].startswith("user="):
            login = row['conf'].split("user=")[1]
        if row['conf'].startswith("password="):
            password = row['conf'].split("password=")[1]

    for result in cypher(plpy, query, params, url, login, password):
        yield result


def cypher_default_server(plpy, query, params):
    """
        Make cypher query and return JSON result
    """
    for result in cypher_with_server(plpy, query, params, None):
        yield result

def node2json(node):
    """
        Convert a node to json
    """
    jsonResult = "{"
    jsonResult += '"id": ' + json.dumps(node._id) + ','
    jsonResult += '"labels": ' + json.dumps(node._labels, default=set_default) + ','
    jsonResult += '"properties": ' + json.dumps(node._properties, default=set_default)
    jsonResult += "}"

    return jsonResult


def relation2json(rel):
    """
        Convert a relation to json
    """
    jsonResult = "{"
    jsonResult += '"id": ' + json.dumps(rel._id) + ','
    jsonResult += '"type": ' + json.dumps(rel._type) + ','
    jsonResult += '"properties": ' + json.dumps(rel._properties, default=set_default)
    jsonResult += "}"

    return jsonResult

def path2json(path):
    """
        Convert a path to json
    """
    jsonResult = "["
    if segment.start() is not None:
        jsonResult += node2json(segment.start())

    for segment in path:
        jsonResult += "," + relation2json( segment.relationship() )
        jsonResult += "," + node2json( segment.end() )

    jsonResult += "]"

    return jsonResult

def set_default(obj):
    """
        For JSON Serializer : convert set to list
    """
    if isinstance(obj, set):
        return list(obj)
    raise TypeError
