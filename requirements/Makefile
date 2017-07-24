.PHONY: all check clean


objects = $(wildcard *.in)
outputs = $(objects:.in=.txt)


all: $(outputs)


%.txt: %.in
	pip-compile -v --output-file $@ $<


develop.txt: base.txt


check:
	@which pip-compile > /dev/null


clean:
	-rm *.txt
