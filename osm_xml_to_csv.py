
# coding: utf-8

# In[ ]:

import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET
from collections import defaultdict
from geopy.geocoders import Nominatim
geolocator = Nominatim()
from time import sleep
import schema

from osm_xml_to_csv import *

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


def update_city_name(name):
    
    if (', TN' in name):
        name = name.replace(', TN', '')
        
    if (', Tennessee' in name):
        name = name.replace(', Tennessee', '')
        
    if (name == 'LaVergne'):
        name = 'La Vergne'
        
    if (name == 'Mount Joliet'):
        name = 'Mount Juliet'
        
    if (not name[0].isupper()):
        name = name.capitalize()
        
    if ( (name == 'Thompson"s Station') or (name == 'Thompsons Station') ):
        name = "Thompson's Station"
        
    return name

def update_name(name):
    mapping = { "Ave": "Avenue",
            "AVENUE": "Avenue",
            "ave": "Avenue",
            "avenue": "Avenue",
            "BLVD": "Boulevard",
            "Blvd": "Boulevard",
            "Cir": "Circle",
            "Ct": "Court",
            "Dr": "Drive",
            "hills": "Hills",
            "Hwy": "Highway",
            "Hwy.": "Highway",
            "Ln": "Lane",
            "pike": "Pike",
            "Pk": "Pike",
            "Pkwy": "Parkway",
            "Pky": "Parkway",
            "Rd.": "Road",
            "Rd": "Road",
            "S": "South",
            "St": "Street",
            "St.": "Street",
            "st": "Street",
            "W": "West"
            }
    for key in mapping.keys():
        if (name.endswith(key)):
            name = name.replace(' '+key, ' ' + mapping[key])
    
    return name


def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements
    #node_attr_fields = [id, user, uid, version, lat, lon, timestamp, changeset]

    # YOUR CODE HERE
    if element.tag == 'node':
        node_attribs = {}
        #print element.attrib
        for key in element.attrib.keys():
            #print key
            if (key in node_attr_fields):
                node_attribs[key] = element.attrib[key]
        #print node_attribs
        #print ""
        for child in element.iter('tag'):
            tags_dict = {}
            #print child.tag
            #print child.attrib
            tags_dict['id'] = element.attrib['id']
            if (('k' in child.attrib.keys()) and (child.attrib['k'] == 'addr:street')):
                tags_dict['value'] = update_name(child.attrib['v'])
            else:
                tags_dict['value'] = child.attrib['v']
            
            if (('k' in child.attrib.keys()) and (child.attrib['k'] == 'addr:city')):
                tags_dict['value'] = update_city_name(child.attrib['v'])
            else:
                tags_dict['value'] = child.attrib['v']
            
            if (not(problem_chars.search(child.attrib['k']))):
                if (':' in child.attrib['k']):
                    #print child.attrib['k']
                    #print type(child.attrib['k'].find(':'))
                    #print child.attrib['k'][0:child.attrib['k'].find(':')]
                    #print child.attrib['k'][child.attrib['k'].find(':')+1:len(child.attrib['k'])]
                    
                    tags_dict['key'] = child.attrib['k'][child.attrib['k'].find(':')+1:len(child.attrib['k'])]
                    tags_dict['type'] = child.attrib['k'][0:child.attrib['k'].find(':')]
                
                else:
                    tags_dict['key'] = child.attrib['k']
                    tags_dict['type'] = 'regular'
                    
            tags += [tags_dict]
        #print tags
        #print ""
        #pprint.pprint({'node': node_attribs, 'node_tags': tags})
        #print ""
        return {'node': node_attribs, 'node_tags': tags}
        
    elif element.tag == 'way':
        way_attribs = {}
        for key in element.attrib.keys():
            if (key in way_attr_fields):
                way_attribs[key] = element.attrib[key]
          
        nd_index = 0     
        for child in element.iter():
            #print child.tag
            
            if (child.tag == 'nd' and child.tag != None):
                #print child.attrib
                way_nodes_dict = {}
                #- id: the top level element (way) id
                #- node_id: the ref attribute value of the nd tag
                #- position: the index starting at 0 of the nd tag i.e. what order the nd tag appears within the way element
                way_nodes_dict['id'] = element.attrib['id']
                way_nodes_dict['node_id'] = child.attrib['ref']
                way_nodes_dict['position'] = nd_index
            
                way_nodes += [way_nodes_dict]
            
            if (child.tag == 'tag' and child.tag != None):
                tags_dict = {}
                #print child.tag
                #print child.attrib
                tags_dict['id'] = element.attrib['id']
                if (('k' in child.attrib.keys()) and (child.attrib['k'] =='addr:street')):
                    tags_dict["value"] = update_name(child.attrib["v"])
                else:
                    tags_dict['value'] = child.attrib['v']
                
                if (('k' in child.attrib.keys()) and (child.attrib['k'] == 'addr:city')):
                    tags_dict['value'] = update_city_name(child.attrib['v'])
                else:
                    tags_dict['value'] = child.attrib['v']
                
                if (not(problem_chars.search(child.attrib['k']))):
                    if (':' in child.attrib['k']):
                        #print child.attrib['k']
                        #print type(child.attrib['k'].find(':'))
                        #print child.attrib['k'][0:child.attrib['k'].find(':')]
                        #print child.attrib['k'][child.attrib['k'].find(':')+1:len(child.attrib['k'])]
                    
                        tags_dict['key'] = child.attrib['k'][child.attrib['k'].find(':')+1:len(child.attrib['k'])]
                        tags_dict['type'] = child.attrib['k'][0:child.attrib['k'].find(':')]
                
                    else:
                        tags_dict['key'] = child.attrib['k']
                        tags_dict['type'] = 'regular'
                    
                tags += [tags_dict]
                
            nd_index += 1
        #pprint.pprint({'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags})
        #print ""
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file,          codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file,          codecs.open(WAYS_PATH, 'w') as ways_file,          codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file,          codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        #validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            #print el
            if el:
                #if validate is True:
                    #validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    process_map(OSM_PATH, validate=True)

