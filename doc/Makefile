.SUFFIXES:.pdf

all: thesis.pdf

thesis.pdf: thesis.tex
	pdflatex thesis
	bibtex thesis
	pdflatex thesis
	latex thesis
	dvips thesis
	ps2pdf thesis.ps
