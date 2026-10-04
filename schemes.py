from __future__ import annotations


def ektp():
    return {"appropriation": 5.9e12, "nodes": [
        {"id": "budget", "name": "State budget", "parent": None, "share": 1, "capture": .004, "retain": .01, "audit": .30},
        {"id": "kemen", "name": "Kemendagri", "parent": "budget", "share": 1, "capture": .03, "retain": .06, "audit": .18},
        {"id": "consortium", "name": "Consortium", "parent": "kemen", "share": 1, "capture": .25, "retain": .10, "audit": .08},
        {"id": "vendors", "name": "Vendors", "parent": "consortium", "share": .6, "capture": .22, "retain": .08, "audit": .05,
         "markup": .45, "linkedOwner": "insider", "transfers": [{"to": "recipients", "rate": .5}]},
        {"id": "recipients", "name": "Recipients", "parent": "consortium", "share": .4, "capture": .55, "retain": 0, "audit": .03,
         "linkedOwner": "nominees"},
    ]}


def launder():
    return {"appropriation": 6e12, "nodes": [
        {"id": "ministry", "name": "Ministry", "parent": None, "share": 1, "capture": .01, "retain": .02, "audit": .30},
        {"id": "consortium", "name": "Consortium", "parent": "ministry", "share": 1, "capture": .20, "retain": .10, "audit": .08},
        {"id": "shell", "name": "Shell firms", "parent": "consortium", "share": 1, "capture": .10, "retain": .05, "audit": .10, "markup": .5},
        {"id": "changers", "name": "Money changers", "parent": "shell", "share": 1, "capture": .15, "retain": .10, "audit": .05},
        {"id": "recipients", "name": "Recipients", "parent": "changers", "share": 1, "capture": .50, "retain": 0, "audit": .03,
         "linkedOwner": "nominees"},
    ]}


def ghost():
    return {"appropriation": 1e12, "nodes": [
        {"id": "budget", "name": "Budget", "parent": None, "share": 1, "capture": .01, "retain": .02, "audit": .35},
        {"id": "dept", "name": "Dept", "parent": "budget", "share": 1, "capture": .03, "retain": .05, "audit": .25},
        {"id": "district", "name": "District", "parent": "dept", "share": 1, "capture": .08, "retain": .10, "audit": .15},
        {"id": "school", "name": "Ghost school", "parent": "district", "share": 1, "capture": .05, "retain": 0, "audit": .05,
         "frontline": True, "ghost": True},
    ]}


def kickback():
    return {"appropriation": 2e12, "nodes": [
        {"id": "budget", "name": "Budget", "parent": None, "share": 1, "capture": .01, "retain": .02, "audit": .35},
        {"id": "agency", "name": "Agency", "parent": "budget", "share": 1, "capture": .06, "retain": .10, "audit": .20},
        {"id": "vendor", "name": "Vendor", "parent": "agency", "share": 1, "capture": .30, "retain": .10, "audit": .06,
         "markup": .5, "linkedOwner": "insider", "transfers": [{"to": "agency", "rate": .5}]},
    ]}


def embezzle():
    return {"appropriation": 2e12, "nodes": [
        {"id": "budget", "name": "Budget", "parent": None, "share": 1, "capture": .01, "retain": .02, "audit": .35},
        {"id": "agency", "name": "Agency", "parent": "budget", "share": 1, "capture": .30, "retain": .10, "audit": .06},
        {"id": "office", "name": "Office", "parent": "agency", "share": 1, "capture": .28, "retain": .10, "audit": .05},
        {"id": "unit", "name": "Unit", "parent": "office", "share": 1, "capture": .02, "retain": .90, "audit": .30},
    ]}


LIBRARY = [ektp, launder, ghost, kickback, embezzle]


def seed_bank():
    return [f() for f in LIBRARY]