#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

#define SOURCE "/proc/net/dev"
#define DBDIR "/var/lib/trafcount"

int get_count(FILE *fp, const char dev[16], unsigned long int *u_in, unsigned long int *u_out);

struct entry {
    unsigned int date;
    unsigned long int in_count;
    unsigned long int out_count;
    unsigned long int in_bytes;
    unsigned long int out_bytes;
};

int main(int argc, char **argv) {
    FILE *sfp;
    FILE *dfp;
    char dev[16];
    char db[128];
    int c;
    int i;
    time_t t;
    struct tm *tm;
    char date[16];
    unsigned int u_date;
    unsigned long int u_in;
    unsigned long int u_out;
    struct entry cur_entry;

    if (argc < 2) {
	fprintf(stderr, "Usage: %s eth0 ...\n", argv[0]);
	exit(1);
    }

    t = time(NULL);
    tm = localtime(&t);
    if ((strftime(date, sizeof(date), "%Y%m%d", tm)) == 0) {
        fprintf(stderr, "Error in strftime\n");
        exit(1);
    }

    u_date = (unsigned int) strtol(date, NULL, 10);

    if ((sfp = fopen(SOURCE, "r")) == NULL) {
	fprintf(stderr, "Error opening source file: %s\n", SOURCE);
	exit(1);
    }
    
    for (c = 1; c < argc; c++) {
	u_in = 0;
	u_out = 0;
	
	snprintf(dev, sizeof(dev), "%s:", argv[c]);

	if (get_count(sfp, dev, &u_in, &u_out)) {
    	    fprintf(stderr, "Error: empty count (%s)\n", argv[c]);
    	    continue;
	}
    
	snprintf(db, sizeof(db), "%s/%s.db", DBDIR, argv[c]);
	memset(&cur_entry, 0, sizeof(struct entry));

	if (dfp = fopen(db, "rb+")) {
	    /* Update db */
	    do
		fread(&cur_entry, sizeof(struct entry), 1, dfp);
	    while (!feof(dfp) && cur_entry.date && (cur_entry.date != u_date));
	
	    if (!cur_entry.date || (cur_entry.date == u_date))
		/* Back to begin this entry */
		fseek(dfp, sizeof(struct entry) * -1, SEEK_CUR);
	    else if (feof(dfp)) {
    		fprintf(stderr, "Error: db %s is full\n", db);
    		fclose(dfp);
    		continue;
	    }
	
	    cur_entry.date = u_date;
	    if (cur_entry.in_count && (cur_entry.in_count < u_in))
		cur_entry.in_bytes += u_in - cur_entry.in_count;
	    if (cur_entry.out_count && (cur_entry.out_count < u_out))
		cur_entry.out_bytes += u_out - cur_entry.out_count;
	    cur_entry.in_count = u_in;
	    cur_entry.out_count = u_out;

	    fwrite(&cur_entry, sizeof(struct entry), 1, dfp);
	
	} else if (dfp = fopen(db, "wb")) {
	    /* Initialize db */
	    for (i = 0; i < 365 * 100; i++)
		fwrite(&cur_entry, sizeof(struct entry), 1, dfp);
	} else {
    	    fprintf(stderr, "Error opening db file: %s\n", db);
    	    continue;
	}
	
	fclose(dfp);
    }
    
    fclose(sfp);
    
    return 0;
}

int get_count(FILE *fp, const char dev[16], unsigned long int *u_in, unsigned long int *u_out) {
    char *line;
    char buff[256];
    char *colon;
    char *in = NULL;
    char *out = NULL;
    int i;

    while (line = fgets(buff, sizeof(buff), fp)) {
	/* Trim leading whitespace */
	while(isspace(line[0])) line++;

	if (colon = strchr(line, ':')) {
	    if (!strncmp(line, dev, strlen(dev))) {
		in = strtok(colon + 1, " ");
		for (i = 0; i < 8; i++)
		    out = strtok(NULL, " ");
		break;
	    }
	}
    }

    rewind(fp);
    
    if (!in || !out)
	return 1;
    
    *u_in = strtoul(in, NULL, 10);
    *u_out = strtoul(out, NULL, 10);
    
    return 0;
}
