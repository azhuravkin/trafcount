#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

#define SOURCE "/proc/net/dev"
#define DBDIR "/var/lib/trafcount"
#define RECORDS (365 * 1)

int get_counts(FILE *fp, const char dev[16], unsigned long int *in_count, unsigned long int *out_count);
int search(FILE *fp, unsigned int date);

struct record {
    unsigned int date;
    unsigned long int in_count;
    unsigned long int out_count;
    unsigned long long int in_bytes;
    unsigned long long int out_bytes;
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
    unsigned long int in_count;
    unsigned long int out_count;
    struct record cur_record;

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
	in_count = 0;
	out_count = 0;

	snprintf(dev, sizeof(dev), "%s:", argv[c]);

	if (get_counts(sfp, dev, &in_count, &out_count)) {
	    fprintf(stderr, "Error: device %s not exist\n", argv[c]);
	    continue;
	}

	memset(&cur_record, 0, sizeof(struct record));
	snprintf(db, sizeof(db), "%s/%s.db", DBDIR, argv[c]);

	if (dfp = fopen(db, "rb+")) {
	    /* Update db */

	    if (search(dfp, u_date)) {
		fread(&cur_record, sizeof(struct record), 1, dfp);
		fseek(dfp, sizeof(struct record) * -1, SEEK_CUR);
	    }

	    cur_record.date = u_date;
	    if (cur_record.in_count && (cur_record.in_count < in_count))
		cur_record.in_bytes += in_count - cur_record.in_count;
	    if (cur_record.out_count && (cur_record.out_count < out_count))
		cur_record.out_bytes += out_count - cur_record.out_count;
	    cur_record.in_count = in_count;
	    cur_record.out_count = out_count;

	    /* Back to begin this record */
	    fwrite(&cur_record, sizeof(struct record), 1, dfp);

	} else if (dfp = fopen(db, "wb")) {
	    /* Initialize db */
	    for (i = 0; i < RECORDS; i++)
		fwrite(&cur_record, sizeof(struct record), 1, dfp);
	} else {
	    fprintf(stderr, "Error opening db file: %s\n", db);
	    continue;
	}

	fclose(dfp);
    }

    fclose(sfp);

    return 0;
}

int get_counts(FILE *fp, const char dev[16], unsigned long int *in_count, unsigned long int *out_count) {
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

    *in_count = strtoul(in, NULL, 10);
    *out_count = strtoul(out, NULL, 10);

    return 0;
}

int search(FILE *fp, unsigned int date) {
    /* Ищем нужную позицию в db */
    int i;
    int fill = 0;
    struct record rec;
    unsigned int dates[RECORDS];

    memset(&rec, 0, sizeof(struct record));

    for (i = 0; ((i < RECORDS) && (!feof(fp))); i++) {
	fread(&rec, sizeof(struct record), 1, fp);
	if (rec.date) fill = 1;
	dates[i] = rec.date;
    }

    /* Если db полностью пустая, переходим в начало файла */
    if (!fill) {
	rewind(fp);
	return 0;
    }

    /* Если в db есть нужная запись, переходим на эту позицию и возвращаем 1, чтобы считать запись */
    for (i = 0; i < RECORDS; i++)
	if (dates[i] == date) {
	    fseek(fp, sizeof(struct record) * i, SEEK_SET);
	    return 1;
	}

    /* Если дата в текущей записи меньше чем в предыдущей, переходим на позицию текущей */
    for (i = 1; i < RECORDS; i++)
	if (dates[i] < dates[i - 1]) {
	    fseek(fp, sizeof(struct record) * i, SEEK_SET);
	    return 0;
	}

    /* Либо переходим в начало файла */
    rewind(fp);
    return 0;
}
