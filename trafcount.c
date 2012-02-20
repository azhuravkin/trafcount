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
	u_int32_t date;
	u_int64_t in_count;
	u_int64_t out_count;
	u_int64_t in_bytes;
	u_int64_t out_bytes;
};

static int search(FILE *database, u_int32_t date) {
	/* Ищем нужную позицию в db */
	int i;
	struct record rec;
	u_int32_t dates[RECORDS];

	memset(&rec, 0, sizeof(struct record));

	/* Сохраняем в массив даты записей */
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

static int update_db(char *db, u_int32_t date, const char *chain, u_int64_t count) {
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

static int get_counts(u_int32_t date) {
	iptc_handle_t h;
	const char *chain = NULL;

	h = iptc_init("filter");

	if (!h)
		return 1;

	for (chain = iptc_first_chain(&h); chain; chain = iptc_next_chain(&h)) {
		const struct ipt_entry *e;

		if (strcmp(chain, FROM_CHAIN) && strcmp(chain, TO_CHAIN))
			continue;

		for (e = iptc_first_rule(chain, &h); e; e = iptc_next_rule(e, &h)) {
			char db[128];
			if (e->ip.src.s_addr && !e->ip.dst.s_addr) {
				snprintf(db, sizeof(db), "%s/%u.%u.%u.%u.db", DBDIR, IP_PARTS(e->ip.src.s_addr));
				update_db(db, date, chain, e->counters.bcnt);
			} else if (!e->ip.src.s_addr && e->ip.dst.s_addr) {
				snprintf(db, sizeof(db), "%s/%u.%u.%u.%u.db", DBDIR, IP_PARTS(e->ip.dst.s_addr));
				update_db(db, date, chain, e->counters.bcnt);
			}
		}
	}

	iptc_free(&h);

	return 0;
}

int main(void) {
	time_t t;
	struct tm *tm;
	char date[16];

	/* Формируем текущую дату в формате YYYYMMDD */
	t = time(NULL);
	tm = localtime(&t);
	if ((strftime(date, sizeof(date), "%Y%m%d", tm)) == 0) {
		fprintf(stderr, "Error in strftime()\n");
		return 1;
	}

	return get_counts(atoi(date));
}
