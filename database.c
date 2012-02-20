#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "database.h"

static int search(FILE *database, u_int32_t date) {
    struct header cur;

    /* Пока читается заголовок */
    while (fread(&cur, sizeof(struct header), 1, database)) {
	/* Если нашли нужную дату */
	if (cur.date == date) {
	    /* Переходим на начало заголовка */
	    fseek(database, sizeof(struct header) * -1, SEEK_CUR);
	    return 1;
	}
	/* Перепрыгиваем на следующий заголовок */
	fseek(database, sizeof(struct data) * cur.num, SEEK_CUR);
    }

    return 0;
}

static struct header *update_counts(struct header *cur, int direction, const char *name, u_int64_t count) {
    int i;
    struct data d;

    for (i = 0; i < cur->num; i++) {
	memcpy(&d, &cur->parts[i], sizeof(struct data));

	if (!strcmp(d.name, name)) {
	    if (direction == INCOMING) {
		if (cur->parts[i].in_count && (cur->parts[i].in_count < count))
		    cur->parts[i].in_bytes += count - cur->parts[i].in_count;
		cur->parts[i].in_count = count;
	    } else {
		if (cur->parts[i].out_count && (cur->parts[i].out_count < count))
		    cur->parts[i].out_bytes += count - cur->parts[i].out_count;
		cur->parts[i].out_count = count;
	    }
	    return cur;
	}
    }

    memset(&d, 0, sizeof(struct data));
    strcpy(d.name, name);

    if (direction == INCOMING)
	d.in_count = count;
    else
	d.out_count = count;

    cur->num++;
    cur = realloc(cur, sizeof(struct header) + sizeof(struct data) * cur->num);
    memcpy(&cur->parts[cur->num - 1], &d, sizeof(struct data));

    return cur;
}

int update_db(const char *db, u_int32_t date, const char *name, int direction, u_int64_t count) {
    FILE *fp;
    struct header *cur;

    cur = calloc(1, sizeof(struct header));

    /* Открываем файл на обновление. Если не открылся - открываем на запись */
    if ((fp = fopen(db, "rb+")) == NULL) {
	if ((fp = fopen(db, "wb")) == NULL) {
	    fprintf(stderr, "Error opening db file: %s\n", db);
	    return 1;
	}
    }

    /* Если находим запись с текущей датой */
    if (search(fp, date)) {
	/* Читаем одну запись с текущей позиции */
	fread(cur, sizeof(struct header), 1, fp);

	/* Если данные есть */
	if (cur->num) {
	    /* Выделяем для них место */
	    cur = realloc(cur, sizeof(struct header) + sizeof(struct data) * cur->num);
	    /* И читаем в память */
	    fread(cur->parts, sizeof(struct data), cur->num, fp);
	}

	/* Переходим на начало текущей записи */
	fseek(fp, (sizeof(struct header) + sizeof(struct data) * cur->num) * -1, SEEK_CUR);
    }

    /* Записываем обновлённые данные */
    cur->date = date;
    cur = update_counts(cur, direction, name, count);

    fwrite(cur, sizeof(struct header) + sizeof(struct data) * cur->num, 1, fp);

    fclose(fp);
    free(cur);

    return 0;
}
