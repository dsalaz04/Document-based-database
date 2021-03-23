# Daniel Salazar

import sys
import random
import os.path
import csv
from sys import platform
import shutil
from tempfile import NamedTemporaryFile


class Database():
    def __init__(self):
        self.config_file = None
        self.data_file = None
        self.data_file_name = None
        self.num_records = None
        self.record_size = None
        self.record_size_offset = 1
        self.lineBreak = '\n'

        if platform == "linux" or platform == "linux2":
            # linux
            self.record_size_offset = 1
            self.lineBreak = '\n'
        elif platform == "darwin":
            # OS X
            self.record_size_offset = 1
            self.lineBreak = '\n'
        elif platform == "win32":
            self.record_size_offset = 2
            self.lineBreak = '\n'

    # Windows...

    def start(self):
        ans = True
        while ans:
            print("""
      1. Create new database
      2. Open database
      3. Close database
      4. Display record
      5. Update record
      6. Create report
      7. Add record
      8. Delete record
      9. Quit
      """)
            ans = input("Select an option from the menu, then press 'enter': ")
            if ans == "1":
                self.create()
            elif ans == "2":
                self.openDatabase()
            elif ans == "3":
                self.closeDatabase()
            elif ans == "4":
                self.displayRecord()
            elif ans == "5":
                self.updateRecord()
            elif ans == "6":
                self.createReport()
            elif ans == "7":
                self.addRecord()
            elif ans == "8":
                self.deleteRecord()
            elif ans == "9":
                print("\nQuitting...")
                exit()

            elif ans != "":
                print("\n Not Valid Choice")

    # Options 1-8

    # Option 1, create database from .csv file using csv parsing library
    def create(self):
        file_name = input("Please type in your file name(no extension) and press 'enter': ")
        csv_file = open(file_name + ".csv", 'r+')
        print("\nYou have successfully created your database with information from the following file: ")
        print(file_name + ".csv")

        # read first line
        csv_reader = csv.reader(csv_file, quotechar='"', quoting=csv.QUOTE_ALL, delimiter=",")
        field_names = next(csv_reader)
        num_fields = len(field_names)

        # get largest fields, number of records,

        largest = [0] * num_fields
        num_records = 0
        for fields in csv_reader:
            for index, field in enumerate(fields):
                largest[index] = max(largest[index], len(field))

            num_records += 1
        csv_file.close()
        # write size of fields, number of records
        # record size is the sum of the fields, plus the number of fields - 1 for the commas, plus 1 for the newline
        record_size = sum(largest) + len(largest) - 1 + 1
        line_to_be_written = [str(record_size), str(num_records)] + field_names
        for field_index in range(num_fields):
            line_to_be_written.append(str(largest[field_index]))
        line_to_be_written.append(str(num_fields))
        #print(line_to_be_written)

        # so it should look like [record_size, number of entries, field_1, field..., size_1, ...., num_fields]
        config = open(file_name + ".config", 'w+')
        config_file = csv.writer(config, delimiter=",", quotechar='"')
        config_file.writerow(line_to_be_written)
        config.close()

        # now we should create the data file
        csv_file = open(file_name + ".csv", 'r')
        csv_reader = csv.reader(csv_file, delimiter=",", quotechar='"')
        # skip first line
        next(csv_reader)
        data_file = open(file_name + ".data", 'w+')
        data_writer = csv.writer(data_file, delimiter=",", quotechar='"')
        for data in csv_reader:
            res = []
            # print(data)
            for index, item in enumerate(data):
                formatted_string = "{:" + str(largest[index]) + "s}"
                item = item.replace(',', '')
                res.append(formatted_string.format(item))

            data_writer.writerow(res)

        data_file.close()
        csv_file.close()

    # Option 2, prompt user for .config filename and open database based off it
    def openDatabase(self):

        if (self.data_file and self.data_file.closed == False):
            print("A database is already open. Please close it before opening another instance.")
            return

        file_name = input("Please enter the filename(no extension) for the previously created config file and press 'enter': ")
        self.data_file_name = file_name + ".data"

        if not os.path.isfile(file_name + ".config"):
            print(file_name + ".config not found")
            return

        self.config_file = open(file_name + ".config", 'a+')
        self.config_file.seek(0, 0)
        data = self.config_file.readline().split(',')
        self.data_file = open(file_name + ".data", 'r+')
        #print(data)
        self.record_size = int(data[0])
        self.num_records = int(data[1])
        self.config_file.seek(0, 0)

        print("\nYou have successfully opened your database with information from the following files: ")
        print(file_name + ".config")
        print(file_name + ".data")

    # Option 3, close database

    #### There is a problem here where the file(s) never actually get closed. Neither of the methods actually close the file
    def closeDatabase(self):
        print("Entering Databse close function")
        #print("Attempting to close database...")
        #try:    
        #self.config_file.close()
        #self.data_file.close()
        #print("Database successfully closed")
        #except:
        #    print("There is no database currently opened.")
        if (self.config_file and self.config_file.closed == False):
            self.config_file.close()
            #self.config_file.flush()
        if (self.data_file and self.data_file.closed == False):
            self.data_file.close()
            #self.data_file.flush()
            print("Database successfully closed")

    # Option 4, display record
    def displayRecord(self):

        print("Enter the ID of the record you would like to display: ")
        try:
            ID = int(input())
            print(" ")
        except:
            return False

        try:
            recordNum, record = self.binarySearch(ID)
            if not recordNum == -1:
                print(" ".join(record))
            else:
                print("Record " + str(ID) + " not found")
        except:
            print("Please open the database first(option 2).")

    # Option 5, update a record
    def updateRecord(self):
        try:
            print("Enter the ID of the record you would like to update: ")
            try:
                ID = int(input())
                print(" ")
            except:
                return False

            recordNum, record = self.binarySearch(ID)
            if not recordNum == -1:
                print(" ".join(record))
            else:
                print("Record " + str(ID) + " not found")
                return

            #fieldnames = ['ID', 'Region', 'State', 'Code', 'Vistiors', 'Type', 'Name']
            fieldnames = ['ID', 'Region', 'State', 'Code', 'Name', 'Type', 'Vistiors']
            if record[1] != "NONE":
                while True:
                    print("---------------------------")
                    print("1) Region")
                    print("2) State")
                    print("3) Code")
                    print("4) Name")
                    print("5) Type")
                    print("6) Visitors")
                    print("0) Done updating fields")
                    print("---------------------------")
                    print("Enter the object you would like to update(1-6), 0 to finish updating fields: ")
                    while True:
                        try:
                            field_id = int(input())
                            if field_id < 0 or field_id > 6:
                                continue
                            break
                        except:
                            continue
                    if field_id == 0:
                        break
                    while True:
                        field_content = input("Enter the new content for this field: ")
                        try:
                            if field_id == 1 or field_id == 2:
                                if len(field_content) > 2:
                                    continue
                                field_content = field_content.ljust(2 - len(field_content))
                                break
                            if field_id == 3:
                                if len(field_content) > 4:
                                    continue
                                field_content = field_content.ljust(4 - len(field_content))
                                break
                            if field_id == 4:
                                if len(field_content) > 83:
                                    continue
                                field_content = field_content.ljust(83 - len(field_content))
                                break
                            if field_id == 5:
                                if len(field_content) > 37:
                                    continue
                                field_content = field_content.ljust(37 - len(field_content))
                                break
                            if field_id == 6:
                                if len(field_content) > 9:
                                    continue
                                field_content = field_content.ljust(9 - len(field_content))
                                break
                        except:
                            continue

                    record[field_id] = field_content
                    # data = ','.join(record.values())
                    data = ','.join(record)
                    self.updateRecordInFile(recordNum, data)
        except:
            print("Please open the database first(option 2).")        

    # Option 6, create report
    def createReport(self):
        try:
            print("Creating report...\n")

            count = 0
            row = 0
            while count < 10:
                record, success = self.getRecord(row)
                row = row + 1
                if success == True:
                    if len(record) > 1:
                        print(" ".join(record))
                        count = count + 1
        except:
            print("Please open the database first(option 2).")

    # Option 7, add record
    def addRecord(self):
        try:
            print("Enter the ID for the new record: ")
            while True:
                try:
                    ID = int(input())
                except:
                    continue
                checkid, test = self.binarySearch(ID)
                if checkid > 0 or len(str(ID)) > 7:
                    print("ID not valid")
                    continue
                break
            rowdata = str(ID).ljust(7 - len(str(ID)))
            regionNew = self.getnewValue("Enter the two letter region: ", 2)
            rowdata = rowdata + "," + regionNew
            stateNew = self.getnewValue("Enter the two letter state: ", 2)
            rowdata = rowdata + "," + stateNew
            codeNew = self.getnewValue("Enter the four letter code: ", 4)
            rowdata = rowdata + "," + codeNew
            nameNew = self.getnewValue("Enter the name: ", 83)
            rowdata = rowdata + "," + nameNew
            typeNew = self.getnewValue("Enter the type: ", 37)
            rowdata = rowdata + "," + typeNew
            visitorsNew = self.getnewValue("Enter the number of visitors: ", 9)
            rowdata = rowdata + "," + visitorsNew

            #Name, type, visitors

            recordNum = self.searchEmptyRecord(ID)
            if recordNum == -1:
                self.reorganizeFile()
                recordNum = self.searchEmptyRecord(ID)

            self.updateRecordInFile(recordNum, rowdata)
            print("Record added")
        except:
            print("Please open the database first(option 2).")

    def getnewValue(self, desc, length):
        print(desc)
        while True:
            if length == 9:
                try:
                    newval = int(input())
                except:
                    continue
            else:
                newval = input()
            if length < 5:
                newval = newval.replace(' ', '')
            if len(str(newval)) > length:
                continue
            newval = str(newval)
            newval = newval.ljust(length - len(newval))
            return newval

    # Option 8, delete record
    def deleteRecord(self):
        try:
            print("Enter the ID of the record you would like to delete: ")
            try:
                ID = int(input())
            except:
                return False
            recordNum, record = self.binarySearch(ID)
            if recordNum == -1:
                print("Record " + str(ID) + " not found")
            else:
                self.deleteRecordInFile(recordNum)
                print("Record " + str(ID) + " deleted")
        except:
            print("Please open the database first(option 2).")

    # Helper functions
    
    # Binary Search
    def binarySearch(self, name):
        filesize = os.path.getsize(self.data_file_name)
        rows = filesize / (self.record_size + self.record_size_offset)
        rows = int(rows)
        self.num_records = rows

        middle = 0
        low = 0
        # high=self.num_records-1
        high = rows - 1
        Found = False

        middle = (low + high) // 2
        while not Found and high >= low and middle >= low:
            record, Success = self.getRecord(middle)
            if not Success:
                break
            if len(record) > 1:
                middleidnum = int(record[0])
            else:
                # high = high - 1
                middle = middle - 1
                continue

            if middleidnum == name:
                Found = True
            if middleidnum < name:
                low = middle + 1
            if middleidnum > name:
                high = middle - 1

            middle = (low + high) // 2

        if (Found == True):
            return middle, record  # the record number of the record
        else:
            return -1, ""

    # Search Empty Place
    def searchEmptyRecord(self, ID):
        row = 0
        previousEmptyRow = -1

        while row < self.num_records:
            record, Success = self.getRecord(row)
            if not Success:
                return -1

            if len(record) > 1:
                curID = int(record[0])
                if curID > ID:
                    return previousEmptyRow
                else:
                    previousEmptyRow = -1
            else:  # empty record
                previousEmptyRow = row

            row = row + 1

        return row

    def getRecord(self, recordNum):
        Success = False
        f = open(self.data_file_name)
        #if (self.data_file.closed == true):
        #    return
        csv_reader = csv.reader(f)

        if recordNum >= 0 and recordNum < self.num_records:
            f.seek((self.record_size + self.record_size_offset) * recordNum)  # offset from the beginning of the file
            record = next(csv_reader)
            Success = True
            return record, Success

        #f.close()
        return [], Success

    def updateRecordInFile(self, recordNum, record):
        Success = False
        recordLen = len(record)
        if recordLen > self.record_size:
        #if recordLen < self.record_size:
            print("Updating record length is invalid")
            return False
        elif recordLen < self.record_size:
            record = record + ' ' * (self.record_size - recordLen)
            print("Record updated")

        f = open(self.data_file_name, 'r+')
        record = record + self.lineBreak

        if recordNum >= 0 and recordNum < self.num_records:
            f.seek((self.record_size + self.record_size_offset) * recordNum)  # offset from the beginning of the file
            f.write(record)
            Success = True
        f.close()

        # self.data_file = open(self.data_file_name, 'a+')
        # self.data_file.seek(0, 0)

        return Success

    def deleteRecordInFile(self, recordNum):
        record = ' ' * self.record_size
        self.updateRecordInFile(recordNum, record)

    def reorganizeFile(self):
        tempfile = NamedTemporaryFile(mode='r+', delete=False)
        # tempfile = open("test.txt", "w+")
        # self.data_file.close()

        emptyRow = ' ' * self.record_size + self.lineBreak
        tempfile.write(emptyRow)
        with open(self.data_file_name) as f:
            for line in f:
                removedLine = line.replace(' ', '')
                if len(removedLine) < 2:
                    continue
                line = line.replace(self.lineBreak, '')
                len1 = len(line)
                if len1 < self.record_size:
                    line = line + ' ' * (self.record_size - len1)
                tempfile.write(line + self.lineBreak)
                tempfile.write(emptyRow)

        # self.data_file.close()
        tempfile.close()
        shutil.move(tempfile.name, self.data_file_name)

        # self.data_file = open(self.data_file_name, 'a+')
        # self.data_file.seek(0, 0)


if __name__ == "__main__":
    database = Database()
    database.start()