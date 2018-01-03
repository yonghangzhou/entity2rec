from __future__ import print_function
from SPARQLWrapper import SPARQLWrapper, JSON
import optparse
import codecs
from os import mkdir
import json
from collections import Counter
import operator


class Sparql(object):

    """SPARQL queries to define property list and get property-specific subgraphs"""

    def __init__(self, entities, config_file, dataset, endpoint, default_graph):

        self.entities = entities  # file containing a list of entities

        self.dataset = dataset

        self.wrapper = SPARQLWrapper(endpoint)

        self.wrapper.setReturnFormat(JSON)

        if default_graph:

            self.default_graph = default_graph

            self.wrapper.addDefaultGraph(self.default_graph)

        self.query_prop = "SELECT ?s ?o  WHERE {?s %s ?o. }"

        self.query_prop_uri = "SELECT ?s ?o  WHERE {?s %s ?o. FILTER (?s = %s)}"

        self._define_properties(config_file)

    def _define_properties(self, config_file):

        with codecs.open(config_file, 'r', encoding='utf-8') as config_read:

            property_file = json.loads(config_read.read())

        try:

            self.properties = [i for i in property_file[self.dataset]]
            print(self.properties)

        except KeyError:

            print("No set of properties provided in the dataset")

            self._get_properties()

    def _get_properties(self):  # get frequent properties from sparql endpoint if a list is not provided in config file

        self.properties = []

        self.wrapper.setReturnFormat(JSON)

        c = Counter()

        for entity in self.entities:

            query = 'select distinct ?p ' \
                         'where {{ <{}> ?p ?o. ' \
                         'FILTER(!isLiteral(?o) && regex(STR(?p),' \
                         '"dbpedia.org/ontology") && !regex(STR(?p),' \
                         '"wiki") && !regex(STR(?p),"thumb"))}} '.format(entity)

            self.wrapper.setQuery(query)

            for results in self.wrapper.query().convert()['results']['bindings']:

                prop = results['p']['value']

                c[prop] += 1

        sorted_props = sorted(c.items(), key=operator.itemgetter(1), reverse=True)

        print(sorted_props)

        self.properties.append(sorted_props[0][0])  # add the first ranked property

        for i, (p, count) in enumerate(sorted_props[0:-1]):

            next_p = sorted_props[i+1][0]
            next_count = sorted_props[i+1][1]

            change_rate = (next_count - count) / count

            print(change_rate)

            if change_rate >= - 0.5:  # check whether the freq drop is larger than 50%

                self.properties.append(next_p)

            else:

                break

        self.properties.append("dct:subject")

        print(self.properties)

    def get_property_graphs(self):

        properties = self.properties

        if 'feedback' in properties:
            properties.remove('feedback')  # don't query for the feedback property

        for prop in properties:  # iterate on the properties

            prop_short = prop

            prop_namespace = prop

            if '/' in prop:

                # avoid creating file with a '/' in the name
                prop_short = prop.split('/')[-1]

                # if it is actually a URI, surround by "<>"
                if prop.startswith("http"):
                    prop_namespace = '<' + prop + '>'

            try:
                mkdir('datasets/%s/' % self.dataset)
                mkdir('datasets/%s/graphs' % self.dataset)

            except:
                pass

            with codecs.open('datasets/%s/graphs/%s.edgelist' % (self.dataset, prop_short), 'w',
                             encoding='utf-8') as prop_graph:  # open a property file graph

                for uri in self.entities:

                    uri = '<' + uri + '>'

                    self.wrapper.setQuery(self.query_prop_uri % (prop_namespace, uri))

                    for result in self.wrapper.query().convert()['results']['bindings']:
                        subj = result['s']['value']

                        obj = result['o']['value']

                        print((subj, obj))

                        prop_graph.write('%s %s\n' % (subj, obj))

    @staticmethod
    def get_uri_from_wiki_id(wiki_id):

        sparql = SPARQLWrapper("http://dbpedia.org/sparql")

        sparql.setQuery("""select ?s where {?s <http://dbpedia.org/ontology/wikiPageID> %d
           }""" % int(wiki_id))

        sparql.setReturnFormat(JSON)

        try:
            uri = sparql.query().convert()['results']['bindings'][0]['s']['value']

        except:

            uri = None

        return uri


if __name__ == '__main__':

    parser = optparse.OptionParser()
    parser.add_option('-e', '--entities', dest='entity_file', help='entity file name', default=False)
    parser.add_option('-c', '--config_file', default='config/properties.json', help='Path to configuration file')
    parser.add_option('-k', '--dataset', dest='dataset', help='dataset')
    parser.add_option('-m', '--endpoint', dest='endpoint', help='sparql endpoint')
    parser.add_option('-d', '--default_graph', dest='default_graph', help='default graph', default=False)

    (options, args) = parser.parse_args()

    entities = list()

    with open('datasets/%s/all.dat' % options.dataset, 'r') as read_all:

        for line in read_all:

            line_split = line.strip('\n').split(' ')

            entities.append(line_split[1])

    entities = list(set(entities))

    sparql_query = Sparql(entities, options.config_file, options.dataset, options.endpoint,
                          options.default_graph)

    sparql_query.get_property_graphs()


