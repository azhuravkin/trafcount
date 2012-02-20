all:
	gcc -lsnmp -o trafcount trafcount.c
clean:
	rm -f trafcount
