/* ex: set ts=8 noet: */
/*
 * Copyright 2011 Ryan Flynn <parseerror+github@gmail.com>
 *
 * ngram3bin python bindings
 *
 * Reference: http://starship.python.net/crew/arcege/extwriting/pyext.html
 *			http://docs.python.org/release/2.5.2/ext/callingPython.html
 *			http://www.fnal.gov/docs/products/python/v1_5_2/ext/buildValue.html
 */

#include <Python.h>
#include <stdlib.h>
#include "ngram3bin.h"

#if PY_MAJOR_VERSION >= 3
#define PY3K
#endif

/*
 * obj PyObject wrapper
 */
typedef struct {
	PyObject_HEAD
	struct ngram3map wordmap;
	struct ngram3map ngramap;
	struct ngramword word;
	PyObject *worddict;
} ngram3bin;

static void	 ngram3bin_dealloc(PyObject *self);
static int	 ngram3bin_print  (PyObject *self, FILE *fp, int flags);
#ifndef PY3K
static PyObject *ngram3bin_getattr(PyObject *self, char *attr);
#endif

static PyObject *ngram3bin_new      (PyObject *self, PyObject *args);
static PyObject *ngram3binpy_word2id(PyObject *self, PyObject *args);
static PyObject *ngram3binpy_id2word(PyObject *self, PyObject *args);
static PyObject *ngram3binpy_id2freq(PyObject *self, PyObject *args);
static PyObject *ngram3binpy_freq   (PyObject *self, PyObject *args);
static PyObject *ngram3binpy_like   (PyObject *self, PyObject *args);

static struct PyMethodDef ngram3bin_Methods[] = {
	{ "word2id",	(PyCFunction) ngram3binpy_word2id,	METH_VARARGS,	NULL },
	{ "id2word",	(PyCFunction) ngram3binpy_id2word,	METH_VARARGS,	NULL },
	{ "id2freq",	(PyCFunction) ngram3binpy_id2freq,	METH_VARARGS,	NULL },
	{ "freq",	(PyCFunction) ngram3binpy_freq,		METH_VARARGS,	NULL },
	{ "like",	(PyCFunction) ngram3binpy_like,		METH_VARARGS,	NULL },
	{ "ngram3bin",	(PyCFunction) ngram3bin_new,		METH_VARARGS,	NULL },
	{ NULL,		NULL,					0,		NULL }
};

/*
 * ngram3bin type-builtin methods
 */
PyTypeObject ngram3bin_Type = {
#ifdef PY3K
	PyVarObject_HEAD_INIT(NULL, 0)
#else
	PyObject_HEAD_INIT(NULL)
	0,			/* ob_size					*/
#endif
	"ngram3bin",		/* char *tp_name;				*/
	sizeof(ngram3bin),	/* int tp_basicsize;				*/
	0,			/* int tp_itemsize; not used much		*/
	ngram3bin_dealloc,	/* destructor tp_dealloc;			*/
	ngram3bin_print,	/* printfunc tp_print;				*/
#ifdef PY3K
	0,			/* getattrfunc tp_getattr;	__getattr__	*/
#else
	ngram3bin_getattr,	/* getattrfunc tp_getattr;	__getattr__	*/
#endif
	0,			/* setattrfunc tp_setattr;	__setattr__	*/
	0,			/* cmpfunc tp_compare;		__cmp__		*/
	0,			/* reprfunc tp_repr;		__repr__	*/
	0,			/* PyNumberMethods *tp_as_number;		*/
	0,			/* PySequenceMethods *tp_as_sequence;		*/
	0,			/* PyMappingMethods *tp_as_mapping;		*/
	0,			/* hashfunc tp_hash;		__hash__	*/
	0,			/* ternaryfunc tp_call;		__call__	*/
	0,			/* reprfunc tp_str;		__str__		*/
#ifdef PY3K
	PyObject_GenericGetAttr,/* tp_getattro					*/
	0,			/* tp_setattro					*/
	0,			/* tp_as_buffer					*/
	Py_TPFLAGS_DEFAULT,	/* tp_flags					*/
	0,			/* tp_doc					*/
	0,			/* tp_traverse					*/
	0,			/* tp_clear					*/
	0,			/* tp_richcompare				*/
	0,			/* tp_weaklistoffset				*/
	0,			/* tp_iter					*/
	0,			/* tp_iternext					*/
	ngram3bin_Methods,	/* tp_methods					*/
	0,			/* tp_members					*/
	0,			/* tp_getset					*/
	0,			/* tp_base					*/
	0,			/* tp_dict					*/
	0,			/* tp_descr_get					*/
	0,			/* tp_descr_set					*/
	0,			/* tp_dictoffset				*/
	0,			/* tp_init					*/
	0,			/* tp_alloc					*/
	0,			/* tp_new					*/
#endif
};

struct module_state {
	PyObject *error;
};

#if PY_MAJOR_VERSION >= 3
#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))
#else
#define GETSTATE(m) (&_state)
static struct module_state _state;
#endif

#if 0
static PyObject * error_out(PyObject *m)
{
	struct module_state *st = GETSTATE(m);
	PyErr_SetString(st->error, "something bad happened");
	return NULL;
}
#endif

#if PY_MAJOR_VERSION >= 3

static int ngram3bin_traverse(PyObject *m, visitproc visit, void *arg)
{
	Py_VISIT(GETSTATE(m)->error);
	return 0;
}

static int ngram3bin_clear(PyObject *m)
{
	Py_CLEAR(GETSTATE(m)->error);
	return 0;
}

static struct PyModuleDef moduledef =
{
		PyModuleDef_HEAD_INIT,
		"ngram3bin",
		NULL,
		sizeof(struct module_state),
		ngram3bin_Methods,
		NULL,
		ngram3bin_traverse,
		ngram3bin_clear,
		NULL
};

#define INITERROR return NULL

PyObject *
PyInit_ngram3bin(void)

#else
#define INITERROR return

void
initngram3bin(void)
#endif
{
#ifdef PY3K
	PyObject *module = PyModule_Create(&moduledef);
#else
	PyObject *module = Py_InitModule("ngram3bin", ngram3bin_Methods);
#endif

	if (module == NULL)
		INITERROR;
	struct module_state *st = GETSTATE(module);

	st->error = PyErr_NewException("ngram3bin.Error", NULL, NULL);
	if (st->error == NULL)
	{
		Py_DECREF(module);
		INITERROR;
	}

#ifdef PY3K
	return module;
#endif
}

#ifndef PY3K
PyObject *ngram3bin_getattr(PyObject *self, char *attr)
{
	PyObject *res = Py_FindMethod(ngram3bin_Methods, self, attr);
	return res;
}
#endif

static PyObject * ngram3bin_NEW(void)
{
	ngram3bin *obj = PyObject_NEW(ngram3bin, &ngram3bin_Type);
	obj->wordmap.m = NULL;
	obj->ngramap.m = NULL;
	obj->wordmap.fd = -1;
	obj->ngramap.fd = -1;
	obj->wordmap.size = 0;
	obj->ngramap.size = 0;
	return (PyObject *)obj;
}

static PyObject * worddict_new(struct ngramword w)
{
	PyObject *d = PyDict_New();
	struct wordlen *wl = w.word;
	unsigned long id;
	for (id = 0; id < w.cnt; id++, wl++)
	{
		PyObject *v = PyLong_FromUnsignedLong(id);
		PyObject *k = PyBytes_FromStringAndSize(wl->str, wl->len);
#if 0
		if (id < 10)
			printf("worddict %s(%ld):%lu\n",
				PyBytes_AS_STRING(k), PyBytes_GET_SIZE(k), PyLong_AsLong(v));
#endif
		(void)PyDict_SetItem(d, k, v);
	}
	return d;
}

static PyObject * ngram3bin_new(PyObject *self, PyObject *args)
{
	ngram3bin *obj = (ngram3bin *)ngram3bin_NEW();
	char *wordpath = NULL;
	char *ngrampath = NULL;
	if (PyArg_ParseTuple(args, "ss", &wordpath, &ngrampath))
	{
		obj->wordmap = ngram3bin_init(wordpath);
		obj->word    = ngramword_load(obj->wordmap);
		obj->ngramap = ngram3bin_init(ngrampath);
		obj->worddict = worddict_new(obj->word);
		ngramword_totalfreqs(obj->word, &obj->ngramap);
		Py_INCREF(obj->worddict);
	}
	Py_INCREF(obj);
	return (PyObject *)obj;
}

static void ngram3bin_dealloc(PyObject *self)
{
	ngram3bin *obj = (ngram3bin *)self;
	ngram3bin_fini(obj->wordmap);
	ngramword_fini(obj->word);
	ngram3bin_fini(obj->ngramap);
	PyMem_FREE(self);
}

static int ngram3bin_print(PyObject *self, FILE *fp, int flags)
{
	ngram3bin *obj = (ngram3bin *)self;
	ngram3bin_str(obj->wordmap, fp);
	ngram3bin_str(obj->ngramap, fp);
	return 0;
}

static PyObject *ngram3binpy_word2id(PyObject *self, PyObject *args)
{
	PyObject *res = NULL;
	PyObject *key = PyUnicode_AsUTF8String(PyTuple_GetItem(args, 0));
	if (key)
	{
		ngram3bin *obj = (ngram3bin *)self;
		res = PyDict_GetItem(obj->worddict, key);
	}
	if (!res)
		res = PyLong_FromLong(0);
	Py_INCREF(res);
	return res;
}

static PyObject *ngram3binpy_id2word(PyObject *self, PyObject *args)
{
	PyObject *res = NULL;
	ngram3bin *obj = (ngram3bin *)self;
	unsigned long id = 0;
	if (PyArg_ParseTuple(args, "i", &id))
	{
		const char *word = ngramword_id2word(id, obj->word);
		res = PyUnicode_FromStringAndSize(word, strlen(word));
		Py_INCREF(res);
	}
	return res;
}

static PyObject *ngram3binpy_id2freq(PyObject *self, PyObject *args)
{
	PyObject *res = NULL;
	ngram3bin *obj = (ngram3bin *)self;
	unsigned long id = 0;
	if (PyArg_ParseTuple(args, "i", &id))
	{
		res = PyLong_FromUnsignedLong(obj->word.word[id].freq);
		Py_INCREF(res);
	}
	return res;
}

/*
 * find frequency of (x,y,z)
 */
static PyObject *ngram3binpy_freq(PyObject *self, PyObject *args)
{
	PyObject *res = NULL;
	ngram3bin *obj = (ngram3bin *)self;
	ngram3 find;
	if (PyArg_ParseTuple(args, "iii", find.id+0, find.id+1, find.id+2))
	{
		unsigned long freq = ngram3bin_freq(find, &obj->ngramap);
		res = PyLong_FromUnsignedLong(freq);
		Py_INCREF(res);
	}
	return res;
}

/*
 * given the results of an ngram3_find() call,
 * import them into a python list of 4-tuples [(x,y,z,freq),...]
 */
static PyObject * ngram3_find_res2py(const ngram3 *f)
{
	PyObject *res = PyList_New(0);
	Py_INCREF(res);
	if (f)
	{
		const ngram3 *c = f;
		while (c->freq)
		{
			PyObject *o, *t = PyTuple_New(4);
			int i;
			for (i = 0; i < 3; i++)
			{
				o = PyLong_FromUnsignedLong(c->id[i]);
				PyTuple_SetItem(t, i, o);
				Py_INCREF(o);
			}
			o = PyLong_FromUnsignedLong(c->freq);
			PyTuple_SetItem(t, 3, o);
			Py_INCREF(o);
			PyList_Append(res, t);
			Py_INCREF(t);
			c++;
		}
	}
	return res;
}

static PyObject *ngram3binpy_like(PyObject *self, PyObject *args)
{
	PyObject *res = NULL;
	ngram3bin *obj = (ngram3bin *)self;
	ngram3 find;
	if (PyArg_ParseTuple(args, "iii", find.id+0, find.id+1, find.id+2))
	{
		if (obj->ngramap.m)
		{
			ngram3 *f = ngram3bin_like(find, &obj->ngramap);
			res = ngram3_find_res2py(f);
			free(f);
		}
	}
	return res;
}

