.SUFFIXES:.pdf

all: thesis.pdf

thesis.pdf: thesis.tex
	pdflatex thesis
	bibtex thesis
	pdflatex thesis
	dvipdf thesis
	pdflatex thesis

