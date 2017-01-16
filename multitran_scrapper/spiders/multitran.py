# -*- coding: utf-8 -*-
import scrapy
from scrapy import Request
import csv
import re

# Settings
INPUT_CSV_NAME = 'tmp.csv'  # Path to input file with csv type
# Delimiter and quotechar are parameters of csv file. You should know it if you created the file
CSV_DELIMITER = '	'
CSV_QUOTECHAR = '"'  # '|'
OUTPUT_CSV_NAME = 'output.csv'  # Path to output file with csv type
TRANSLATE_WORD_INDEX = 0  # Index of column which should be translated. Others columns will be copied to output file
EXCEPTED_DICTIONARIES = ['Сленг', 'Разговорное выражение', 'табу']  # Dictionaries which shouldn't be in output


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
        for input_row in self.input_reader:
            if len(input_row) > 0:
                word = input_row[TRANSLATE_WORD_INDEX]
                request = Request("http://www.multitran.com/m.exe?CL=1&s={}&l1=1&l2=2&SHL=2".format(word),
                                  callback=self.translate,
                                  meta={"input_row": input_row})

                requests.append(request)
        return requests

    def translate(self, response):
        input_row = response.meta['input_row'][TRANSLATE_WORD_INDEX]
        # common_row_xpath = '//*/tr/td/table/tr/td/table/tr/td/table/tr/td/table/tr'
        common_row_xpath = '//*/tr[child::td[@class="gray" or @class="trans"]]'
        translate_xpath = 'td[@class="trans"]/a/text()'
        dict_xpath = 'td[@class="subj"]/a/text()'
        nx_gramms_сommon_xpath = "//*/div[@class='middle_col'][3]"
        nx_gramms_status_xpath = "p[child::a]/text()"
        nx_gramms_words_xpath = "a/text()"
        block_name = 0
        for common_row in response.xpath(common_row_xpath):
            dictionary = common_row.xpath(dict_xpath).extract()
            if len(dictionary) > 0:
                if dictionary[0] in EXCEPTED_DICTIONARIES:
                    continue

                # NX grams detection
                nx_gramms_common = response.xpath(nx_gramms_сommon_xpath)
                nx_gramms_status = nx_gramms_common.xpath(nx_gramms_status_xpath).extract()
                nx_gramms = 'цельное слово' if len(nx_gramms_status) == 0 else nx_gramms_status[0] + " : " + "|".join(
                    nx_gramms_common.xpath(nx_gramms_words_xpath).extract())

                output = []
                for translate in common_row.xpath(translate_xpath):
                    output_array = response.meta['input_row'].copy()
                    output_array.append(translate.extract())
                    output_array.append(dictionary[0])
                    output_array.append(str(block_name))
                    output_array.append(nx_gramms)
                    output_array = [x.strip() for x in output_array]
                    output.append(output_array)
                self.output_writer.writerows(output)
            else:
                # block_name = "".join(common_row.xpath('td[@class="gray"]/text()').extract())
                block_name += 1

    def close(self, reason):
        self.input_file.close()
        self.output_file.close()
