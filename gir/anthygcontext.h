/* -*- mode: C; c-basic-offset: 4; indent-tabs-mode: nil; -*- */
/* vim:set et sts=4: */
/* ibus-anthy - The Anthy engine for IBus
 * Copyright (c) 2012-2019 Takao Fujiwara <takao.fujiwara1@gmail.com>
 * Copyright (c) 2012 Peng Huang <shawn.p.huang@gmail.com>
 * Copyright (c) 2012-2013 Red Hat, Inc.
 *
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, see <https://www.gnu.org/licenses/>.
 */

#ifndef __ANTHY_GCONTEXT_H_
#define __ANTHY_GCONTEXT_H_

#include <glib-object.h>
#include <anthy/anthy.h>

/*
 * Type macros.
 */
#define ANTHY_TYPE_GCONTEXT             \
    (anthy_gcontext_get_type ())
#define ANTHY_GCONTEXT(obj)             \
    (G_TYPE_CHECK_INSTANCE_CAST ((obj), ANTHY_TYPE_GCONTEXT, AnthyGContext))
#define ANTHY_GCONTEXT_CLASS(class)     \
    (G_TYPE_CHECK_CLASS_CAST ((class), ANTHY_TYPE_GCONTEXT, AnthyGContextClass))
#define ANTHY_IS_GCONTEXT(obj)          \
    (G_TYPE_CHECK_INSTANCE_TYPE ((obj), ANTHY_TYPE_GCONTEXT))
#define ANTHY_IS_GCONTEXT_CLASS(class)  \
    (G_TYPE_CHECK_CLASS_TYPE ((class), ANTHY_TYPE_GCONTEXT))
#define ANTHY_GCONTEXT_GET_CLASS(obj)   \
    (G_TYPE_INSTANCE_GET_CLASS ((obj), ANTHY_TYPE_GCONTEXT, AnthyGContextClass))

typedef struct _AnthyGContext AnthyGContext;
typedef struct _AnthyGContextPrivate AnthyGContextPrivate;
typedef struct _AnthyGContextClass AnthyGContextClass;

G_BEGIN_DECLS

/**
 * AnthyGContext:
 *
 * An #AnthyGContext is an object that handles conversion strings.
 */
struct _AnthyGContext {
    GInitiallyUnowned parent;

    AnthyGContextPrivate *priv;

    /*< private >*/
    gpointer pdummy[8];
};

struct _AnthyGContextClass {
    GInitiallyUnownedClass parent;

    /*< private >*/
    gpointer pdummy[8];
};

GType           anthy_gcontext_get_type           (void);

/**
 * anthy_gcontext_new:
 * @returns: A newly allocated #AnthyGContext
 *
 * New an #AnthyGobject.
 */
AnthyGContext   *anthy_gcontext_new               (void);

/**
 * anthy_gcontext_set_encoding:
 * @encoding: An encoding
 *
 * Set an encoding.
 */
int             anthy_gcontext_set_encoding       (AnthyGContext *obj,
                                                   int encoding);

/**
 * anthy_gcontext_init_personality:
 *
 * Initialize the personal dictionaries.
 */
void            anthy_gcontext_init_personality   (AnthyGContext *obj);

/**
 * anthy_gcontext_do_set_personality:
 * @dict_name: a Dictionary name
 *
 * Set a personal dictionary.
 */
int             anthy_gcontext_do_set_personality (AnthyGContext *obj,
                                                   const gchar  *dict_name);

/**
 * anthy_gcontext_resize_segment:
 * @nth: nth segment
 * @resize: size
 *
 * Resize the nth segment.
 */
void            anthy_gcontext_resize_segment     (AnthyGContext *obj, 
                                                   int           nth,
                                                   int           resize);
/**
 * anthy_gcontext_set_string:
 * @string: A conversion string
 *
 * Set a conversion string.
 */
int             anthy_gcontext_set_string         (AnthyGContext *obj,
                                                   const gchar * string);
/**
 * anthy_gcontext_get_nr_segments:
 * @returns: The number of the converted segments
 *
 * The number of the converted segments
 */
int             anthy_gcontext_get_nr_segments    (AnthyGContext *obj);

/**
 * anthy_gcontext_get_segment:
 * @nth_seg: Nth segment
 * @nth_lookup: Nth lookup 
 * @returns: A newly assigned string.
 *
 * A newly assigned string with @ntg_seg and @nth_lookup .
 */
gchar *         anthy_gcontext_get_segment        (AnthyGContext *obj,
                                                   int           nth_seg,
                                                   int           nth_lookup);

/**
 * anthy_gcontext_commit_segment:
 * @nth_seg: Nth segment
 * @nth_lookup: Nth lookup
 *
 * Commit a string with @ntg_seg and @nth_lookup.
 */
int             anthy_gcontext_commit_segment     (AnthyGContext *obj,
                                                   int           nth_seg,
                                                   int           nth_lookup);

/**
 * anthy_gcontext_get_nr_candidates:
 * @returns: The number of the candidates
 *
 * The number of the candidates
 */
int             anthy_gcontext_get_nr_candidates  (AnthyGContext *obj,
                                                   int           nth_seg);

/**
 * anthy_gcontext_set_prediction_string:
 * @string: A prediction string
 *
 * Set a prediction string.
 */
int             anthy_gcontext_set_prediction_string
                                                  (AnthyGContext *obj,
                                                   const gchar * string);

/**
 * anthy_gcontext_get_nr_predictions:
 * @returns: The number of the converted segments in the current
 *        prediction string.
 *
 * The number of the converted segments in the current prediction string.
 */
int             anthy_gcontext_get_nr_predictions
                                                 (AnthyGContext *obj);

/**
 * anthy_gcontext_get_prediction:
 * @nth_seg: Nth segment
 * @returns: A newly assigned string.
 *
 * A newly assigned string with @ntg_seg .
 */
gchar *         anthy_gcontext_get_prediction    (AnthyGContext *obj,
                                                  int nth_seg);

/**
 * anthy_gcontext_commit_prediction:
 * @nth_seg: Nth segment
 *
 * Commit a prediction string with @ntg_seg .
 */
int             anthy_gcontext_commit_prediction (AnthyGContext *obj,
                                                  int nth_seg);

/**
 * anthy_gcontext_set_logger:
 * @level: Log level
 *
 * Set Anthy log level.
 */
void            anthy_gcontext_set_logger        (int level);
G_END_DECLS
#endif
