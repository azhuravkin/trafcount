#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <libiptc/libiptc.h>

#define IP_PARTS_NATIVE(n)		\
(unsigned int)((n) >> 24) & 0xFF,	\
(unsigned int)((n) >> 16) & 0xFF,	\
(unsigned int)((n) >> 8)  & 0xFF,	\
(unsigned int)((n) >> 0)  & 0xFF

#define IP_PARTS(n) IP_PARTS_NATIVE(ntohl(n))
#define FROM_CHAIN "FROM_USERS"
#define TO_CHAIN "TO_USERS"

#define RECORDS (365 * 1)

struct record {
	__u32 date;
	__u64 in_count;
	__u64 out_count;
	__u64 in_bytes;
	__u64 out_bytes;
};

static int search(FILE *database, __u32 date) {
	/* Ищем нужную позицию в db */
	int i;
	struct record rec;
	int dates[RECORDS];

	memset(&rec, 0, sizeof(struct record));

	for (i = 0; ((i < RECORDS) && (!feof(database))); i++) {
		fread(&rec, sizeof(struct record), 1, database);
		dates[i] = rec.date;
	}

	/* Если db полностью пустая, переходим в начало файла */
	if (dates[0] == 0) {
		rewind(database);
		return 0;
	}

	/* Если в db есть нужная запись, переходим на эту позицию и возвращаем 1, чтобы считать запись */
	for (i = 0; i < RECORDS; i++)
		if (dates[i] == date) {
			fseek(database, sizeof(struct record) * i, SEEK_SET);
			return 1;
		}

	/* Если дата в последующей записи меньше чем в предыдущей, переходим на позицию последующей */
	for (i = 1; i < RECORDS; i++)
		if (dates[i] < dates[i - 1]) {
			fseek(database, sizeof(struct record) * i, SEEK_SET);
			return 0;
		}

	/* Либо переходим в начало файла */
	rewind(database);

	return 0;
}

static int update_db(char *db, __u32 date, const char *chain, __u64 count) {
	FILE *fp;
	struct record cur;
	int i;

	memset(&cur, 0, sizeof(struct record));

	/* Если файл открылся на обновление - обновляем данные */
	if ((fp = fopen(db, "rb+"))) {
		if (search(fp, date)) {
			/* Читаем одну запись с текущей позиции */
			fread(&cur, sizeof(struct record), 1, fp);
			/* И переходим на её начало */
			fseek(fp, sizeof(struct record) * -1, SEEK_CUR);
		}

		/* Записываем обновлённые данные */
		cur.date = date;

		if (!strcmp(chain, FROM_CHAIN)) {
			if (cur.out_count && (cur.out_count < count))
				cur.out_bytes += count - cur.out_count;
			cur.out_count = count;
		}

		if (!strcmp(chain, TO_CHAIN)) {
			if (cur.in_count && (cur.in_count < count))
				cur.in_bytes += count - cur.in_count;
			cur.in_count = count;
		}

		fwrite(&cur, sizeof(struct record), 1, fp);

	/* Если файл открылся на запись, инициализируем его нулями */
	} else if ((fp = fopen(db, "wb"))) {
		for (i = 0; i < RECORDS; i++)
			fwrite(&cur, sizeof(struct record), 1, fp);
	/* Файл не открылся ни на обновление ни на запись */
	} else {
		fprintf(stderr, "Error opening db file: %s\n", db);
		return 1;
	}

	fclose(fp);

	return 0;
}

static void check_dir(char *year, unsigned long ip) {
    struct stat st;
    char path[128];

    snprintf(path, sizeof(path), "%s/%s", DBDIR, year);

    if (stat(path, &st) == -1)
	    mkdir(path, 0755);

    snprintf(path, sizeof(path), "%s/%s/%u.%u.%u.%u", DBDIR, year, IP_PARTS(ip));

    if (stat(path, &st) == -1)
	    mkdir(path, 0755);
}

static int get_counts(int date, char *year) {
	struct iptc_handle *h;
	const char *chain = NULL;

	h = iptc_init("filter");

	if (!h)
		return 1;

	for (chain = iptc_first_chain(h); chain; chain = iptc_next_chain(h)) {
		const struct ipt_entry *e;

		if (strcmp(chain, FROM_CHAIN) && strcmp(chain, TO_CHAIN))
			continue;

		for (e = iptc_first_rule(chain, h); e; e = iptc_next_rule(e, h)) {
			char db[128];
			if (e->ip.src.s_addr && !e->ip.dst.s_addr && strlen(e->ip.outiface) && !strlen(e->ip.iniface)) {
				snprintf(db, sizeof(db), "%s/%s/%u.%u.%u.%u/%s.db", DBDIR, year, IP_PARTS(e->ip.src.s_addr), e->ip.outiface);
				check_dir(year, e->ip.src.s_addr);
				update_db(db, date, chain, e->counters.bcnt);
			} else if (!e->ip.src.s_addr && e->ip.dst.s_addr && !strlen(e->ip.outiface) && strlen(e->ip.iniface)) {
				snprintf(db, sizeof(db), "%s/%s/%u.%u.%u.%u/%s.db", DBDIR, year, IP_PARTS(e->ip.dst.s_addr), e->ip.iniface);
				check_dir(year, e->ip.dst.s_addr);
				update_db(db, date, chain, e->counters.bcnt);
			}
		}
	}

	iptc_free(h);

	return 0;
}

int main(void) {
	time_t t;
	char date[16];
	char year[8];

	time(&t);
	/* Формируем текущую дату в формате YYYYMMDD */
	if ((strftime(date, sizeof(date), "%Y%m%d", localtime(&t))) == 0) {
		fprintf(stderr, "Error in strftime()\n");
		return 1;
	}

	/* Формируем текущий год YYYY */
	if ((strftime(year, sizeof(year), "%Y", localtime(&t))) == 0) {
		fprintf(stderr, "Error in strftime()\n");
		return 1;
	}

	get_counts(atoi(date), year);

	return 0;
}
