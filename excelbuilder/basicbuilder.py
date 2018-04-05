def null_item_mapper(item, key):
    return item[key]


class BasicBuilder:
    def __init__(self, sheet, data_list):
        self.sheet = sheet
        self.data_list = data_list
        self.headers = []
        self.column_mappings = {}
        self.header_row = 1
        self.first_data_row = 2

    def set_header_row(self, header_row):
        self.header_row = header_row

    def set_first_data_row(self, data_row):
        self.first_data_row = data_row

    def add_header(self, column_letter, title):
        self.headers.append({"column_letter": column_letter, "title": title})

    def map_column(self, column_letter, item_key, mapper=null_item_mapper):
        self.column_mappings[column_letter] = {'key': item_key, 'mapper': mapper}

    def build(self):
        self.__build_headers()
        self.__build_data_rows()

    def __build_headers(self):
        for header in self.headers:
            cell = self.__get_cell_location(header['column_letter'], self.header_row)
            self.sheet[cell] = header['title']

    def __build_data_rows(self):
        for index, item in enumerate(self.data_list):
            row_num = str(index + self.first_data_row)

            for column_letter, item_key_and_mapper in self.column_mappings.items():
                cell = self.__get_cell_location(column_letter, row_num)

                item_mapper = item_key_and_mapper['mapper']
                item_key = item_key_and_mapper['key']

                self.sheet[cell] = item_mapper(item, item_key)

    def __get_cell_location(self, header, row):
        return ("%s%s" % (header, row))
