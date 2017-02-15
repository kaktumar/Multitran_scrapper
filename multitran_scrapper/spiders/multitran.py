# -*- coding: utf-8 -*-
import scrapy
from scrapy import Request
import csv
import re

# Settings
INPUT_CSV_NAME = 'input.csv'  # Path to input file with csv type
# Delimiter and quotechar are parameters of csv file. You should know it if you created the file
CSV_DELIMITER = '	'
CSV_QUOTECHAR = '"'  # '|'
OUTPUT_CSV_NAME = 'output_tmp.csv'  # Path to output file with csv type
TRANSLATE_WORD_INDEX = 0  # Index of column which should be translated. Others columns will be copied to output file
EXCEPTED_DICTIONARIES = ['разг.']  # Dictionaries which shouldn't be in output


class MultitranSpider(scrapy.Spider):
    name = "multitran"
    allowed_domains = ["multitran.ru"]

    def __init__(self):
        self.input_file = open(INPUT_CSV_NAME, 'r')
        self.input_reader = csv.reader(self.input_file, delimiter=CSV_DELIMITER, quotechar=CSV_QUOTECHAR,
                                       quoting=csv.QUOTE_ALL)
        self.output_file = open(OUTPUT_CSV_NAME, 'w')
        self.output_writer = csv.writer(self.output_file, delimiter=CSV_DELIMITER, quotechar=CSV_QUOTECHAR,
                                        quoting=csv.QUOTE_ALL)

    def start_requests(self):
        requests = []
        i = 0
        for input_row in self.input_reader:
            if len(input_row) > 0:
                word = input_row[TRANSLATE_WORD_INDEX]
                request = Request("http://www.multitran.com/m.exe?CL=1&s={}&l1=1&l2=2&SHL=2".format(word),
                                  callback=self.parse,
                                  meta={"input_row": input_row, 'index': i})

                requests.append(request)
                i += 1
        return requests

    def parse(self, response):
        def recommend_translation(translations):
            def calc_value(translate, unigrams):
                words = translate.split()
                return sum([unigrams[w] for w in words]) / len(words)

            unigrams = {}
            for translate in translations:
                for words in translate.split():
                    if unigrams.get(words, None) is None:
                        unigrams[words] = 1
                    else:
                        unigrams[words] += 1

            maxvalue = 0
            result = []
            for i, translate in enumerate(translations):
                value = calc_value(translate, unigrams)
                if value > maxvalue:
                    maxvalue = value
                    result = [i]

            return result

        def get_text(selector):
            return selector.xpath("text()").extract()

        def get_all_leaf_nodes(selector, prev_results=[]):
            results = []
            for child in selector.xpath('*'):
                children = get_all_leaf_nodes(child)
                results.append([get_text(child)] if children.__len__() == 0 else [get_text(child)] + children)

            return results + prev_results

        common_row_xpath = '//*/tr[child::td[@class="gray" or @class="trans"]]'
        translate_xpath = 'td[@class="trans"]'
        dict_xpath = 'td[@class="subj"]/a/text()'
        nx_gramms_сommon_xpath = "//*/div[@class='middle_col'][3]"
        nx_gramms_status_xpath = "p[child::a]/text()"
        nx_gramms_words_xpath = "a[string-length(@title)>0]/text()"
        block_number = 0
        translates = []
        output = []
        for common_row in response.xpath(common_row_xpath):
            dictionary = common_row.xpath(dict_xpath).extract()
            if len(dictionary) > 0:
                if not dictionary[0] in EXCEPTED_DICTIONARIES:
                    # NX grams detection
                    nx_gramms_common = response.xpath(nx_gramms_сommon_xpath)
                    nx_gramms_status = nx_gramms_common.xpath(nx_gramms_status_xpath).extract()
                    nx_gramms = 'цельное слово' if len(nx_gramms_status) == 0 else nx_gramms_status[
                                                                                       0] + " : " + "|".join(
                        nx_gramms_common.xpath(nx_gramms_words_xpath).extract())

                    for translate in common_row.xpath(translate_xpath):
                        print(get_all_leaf_nodes(translate))
                        # output_array = response.meta['input_row'].copy()
                        # output_array.append(translate.extract())
                        # output_array.append(dictionary[0])
                        # output_array.append(str(block_number))
                        # output_array.append(block_name)
                        # output_array.append(nx_gramms)
                        # output_array = [x.strip() for x in output_array]
                        # output.append(output_array)
                        #
                        # translates.append(translate.extract())
            else:
                block_name = "".join(common_row.xpath('td[@class="gray"]/descendant-or-self::text()').extract())
                block_name = block_name[:block_name.find("|")]
                block_number += 1

        # Add recommended flag to every translates
        recommended_translation_indexes = recommend_translation(translates)
        for i, o in enumerate(output):
            o.append('X' if i in recommended_translation_indexes else 'O')

        # Write ready-to-use data to csv file
        self.output_writer.writerows(output)
        print(response.meta['index'])

    def close(self, reason):
        self.input_file.close()
        self.output_file.close()
