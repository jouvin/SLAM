.PHONY: help clean topdf open

help:
	@echo "  topdf       to make standalone PDF file"
	@echo "  clean       to remove all generated but PDF files"
	@echo "  open        to view generated PDF file"

topdf:
	pdftex -output-format pdf -progname pdflatex -file-line-error -interaction errorstopmode rapport.tex

clean:
	rm -f *.log *.aux *.toc

open:
	open rapport.pdf
	
