PYTHON := python3
DB     := build/parks

.PHONY: test demo menu clean

test:
	$(PYTHON) -m unittest discover -s tests

# Import the sample CSV and exercise a few commands.
demo:
	@mkdir -p build
	$(PYTHON) -m docdb import sample/parks.csv $(DB) --key ID
	$(PYTHON) -m docdb schema $(DB)
	$(PYTHON) -m docdb report $(DB) --limit 5

# Import the sample data, then drop into the interactive menu.
menu:
	@mkdir -p build
	$(PYTHON) -m docdb import sample/parks.csv $(DB) --key ID >/dev/null
	$(PYTHON) -m docdb menu $(DB)

clean:
	rm -rf build
