# Document-based-database
Implemented using Python

Objectives
The objectives of this homework are to first, gain experience with how a database works by reading and parsing data from a CSV file and then interpreting the information into a .data file, and then also to gain experience with adding, deleting, and updating records in a database

Approach
I implemented this program using Python 3.0. I used this language because I saw that there is a CSV parsing library available to me in Python that would help make things much easier for me in terms of reading the CSV file and then formatting my data from it. My design is basically as simple as I could possibly make it. The print statement with the main menu options 1-9 at the top of the program, the actual functions from the menu below that, and then the helper functions at the very bottom.

I chose this format coming directly from my config file:
ID,Region,State,Code,Name,Type,Visitors,
7,2,2,4,83,37,9,7

I used the delimiter included in the Python String class. The total record size is the size of all records plus spaces inbetween: 157. Sample record:

15492   IM AZ ORPI Organ Pipe Cactus National Monument    National Monument    17138757

I used the config file just to store the data about the file such as size of record, length of file, and length of individual pieces of data in records. Contents of the config file are as shown:

151,374,ID,Region,State,Code,Name,Type,Visitors,7,2,2,4,83,37,9,7
