/* -*- mode: C; c-basic-offset: 4; indent-tabs-mode: nil; -*- */
/* vim:set et sts=4: */
/* ibus-anthy - The Anthy engine for IBus
 * Copyright (c) 2012-2021 Takao Fujiwara <takao.fujiwara1@gmail.com>
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

#include <glib-object.h>
#include <anthy/anthy.h>

extern void anthy_init_personality (void);
extern int anthy_do_set_personality (const char *id);

#include "anthygcontext.h"

#define ANTHY_GCONTEXT_GET_PRIVATE(o)   \
    ((AnthyGContextPrivate *)anthy_gcontext_get_instance_private (o))

struct _AnthyGContextPrivate {
    anthy_context_t context;
};

static GObject *anthy_gcontext_constructor (GType type,
                                           guint n,
                                           GObjectConstructParam *args);
static void anthy_gcontext_dispose (GObject *gobject);
static void anthy_gcontext_finalize (GObject *gobject);

G_DEFINE_TYPE_WITH_PRIVATE (AnthyGContext,
                            anthy_gcontext,
                            G_TYPE_INITIALLY_UNOWNED)

static void
anthy_gcontext_class_init (AnthyGContextClass *class)
{
    GObjectClass *gobject_class = G_OBJECT_CLASS (class);
    gobject_class->constructor = anthy_gcontext_constructor;
    gobject_class->dispose = anthy_gcontext_dispose;
    gobject_class->finalize = anthy_gcontext_finalize;
}

static void
anthy_gcontext_init (AnthyGContext *obj)
{
    obj->priv = ANTHY_GCONTEXT_GET_PRIVATE (obj);

    anthy_init ();
    obj->priv->context = anthy_create_context ();
}

static GObject *
anthy_gcontext_constructor (GType                   type,
                           guint                   n,
                           GObjectConstructParam  *args)
{
    GObject *object;

    object = G_OBJECT_CLASS (anthy_gcontext_parent_class)->constructor (type, n ,args);
    return object;
}

static void
anthy_gcontext_dispose (GObject *gobject)
{
    G_OBJECT_CLASS (anthy_gcontext_parent_class)->dispose (gobject);
}

static void
anthy_gcontext_finalize (GObject *gobject)
{
    G_OBJECT_CLASS (anthy_gcontext_parent_class)->finalize (gobject);
}

AnthyGContext *
anthy_gcontext_new (void)
{
    GObject *gobject = g_object_new (ANTHY_TYPE_GCONTEXT, NULL);
    return ANTHY_GCONTEXT (gobject);
}

#define ANTHY_OBJECT_FUNCTION_ASSERTIONS() \
{                                                                       \
    g_assert (obj != NULL);                                             \
    g_assert (obj->priv != NULL);                                       \
    g_assert (obj->priv->context != NULL);                              \
}

int
anthy_gcontext_set_encoding (AnthyGContext *obj, int encoding)
{
    ANTHY_OBJECT_FUNCTION_ASSERTIONS ();

    return anthy_context_set_encoding (obj->priv->context, encoding);
}

void
anthy_gcontext_init_personality (AnthyGContext *obj)
{
    ANTHY_OBJECT_FUNCTION_ASSERTIONS ();

    anthy_init_personality ();
}

int
anthy_gcontext_do_set_personality (AnthyGContext *obj, const gchar *dict_name)
{
    ANTHY_OBJECT_FUNCTION_ASSERTIONS ();

    return anthy_do_set_personality (dict_name);
}

void
anthy_gcontext_resize_segment (AnthyGContext *obj,
                               int            nth,
                               int            resize)
{
    ANTHY_OBJECT_FUNCTION_ASSERTIONS ();

    anthy_resize_segment (obj->priv->context, nth, resize);
}

int
anthy_gcontext_set_string (AnthyGContext *obj, const gchar * string)
{
    ANTHY_OBJECT_FUNCTION_ASSERTIONS ();

    return anthy_set_string (obj->priv->context, string);
}

int
anthy_gcontext_get_nr_segments (AnthyGContext *obj)
{
    struct anthy_conv_stat conv_stat = { 0, };

    ANTHY_OBJECT_FUNCTION_ASSERTIONS ();

    anthy_get_stat(obj->priv->context, &conv_stat);
    return conv_stat.nr_segment;
}

gchar *
anthy_gcontext_get_segment (AnthyGContext *obj, int nth_seg, int nth_lookup)
{
    int length;
    static char temp[512];

    ANTHY_OBJECT_FUNCTION_ASSERTIONS ();

    length = anthy_get_segment (obj->priv->context, nth_seg, nth_lookup,
                                temp, sizeof (temp));
    if (length >= 0) {
        return g_strdup (temp);
    } else {
        return NULL;
    }
}

int
anthy_gcontext_commit_segment(AnthyGContext *obj, int nth_seg, int nth_lookup)
{
    ANTHY_OBJECT_FUNCTION_ASSERTIONS ();

    return anthy_commit_segment (obj->priv->context, nth_seg, nth_lookup);
}

int
anthy_gcontext_get_nr_candidates (AnthyGContext *obj, int nth_seg)
{
    struct anthy_segment_stat seg_stat = { 0, };

    ANTHY_OBJECT_FUNCTION_ASSERTIONS ();

    anthy_get_segment_stat (obj->priv->context, nth_seg, &seg_stat);
    return seg_stat.nr_candidate;
}

int
anthy_gcontext_set_prediction_string (AnthyGContext *obj, const gchar * string)
{
    ANTHY_OBJECT_FUNCTION_ASSERTIONS ();

    return anthy_set_prediction_string (obj->priv->context, string);
}

int
anthy_gcontext_get_nr_predictions (AnthyGContext *obj)
{
    struct anthy_prediction_stat seg_stat = { 0, };

    ANTHY_OBJECT_FUNCTION_ASSERTIONS ();

    anthy_get_prediction_stat (obj->priv->context, &seg_stat);
    return seg_stat.nr_prediction;
}

gchar *
anthy_gcontext_get_prediction (AnthyGContext *obj, int nth_seg)
{
    int length;
    static char temp[512];

    ANTHY_OBJECT_FUNCTION_ASSERTIONS ();

    length = anthy_get_prediction (obj->priv->context, nth_seg,
                                   temp, sizeof (temp));
    if (length >= 0) {
        return g_strdup (temp);
    } else {
        return NULL;
    }
}

int
anthy_gcontext_commit_prediction (AnthyGContext *obj, int nth_seg)
{
    ANTHY_OBJECT_FUNCTION_ASSERTIONS ();

    return anthy_commit_prediction (obj->priv->context, nth_seg);
}

void
anthy_gcontext_set_logger (int level)
{
    anthy_set_logger (NULL, level);
}

#undef ANTHY_OBJECT_FUNCTION_ASSERTIONS
