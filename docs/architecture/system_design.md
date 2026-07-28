# AutoForge System Architecture

## Goal

AutoForge is an automation platform that receives Git events,
executes pipelines,
generates source code,
builds projects,
and automatically commits changes.

---

## Flow

GitHub

↓

Webhook

↓

Event Dispatcher

↓

Pipeline

↓

Plugin Manager

↓

Plugin

↓

Workspace

↓

Git Commit

↓

Git Push

↓

Pull Request

---

## Core Modules

CLI

Configuration

Plugin Framework

Pipeline Engine

Task Scheduler

Event Dispatcher

---

## Services

Webhook Service

Generator Service

Git Service

Build Service

Template Service

---

## Infrastructure

Logging

Filesystem

Database

Docker

Redis

Message Queue

---

## Future

AI Generator

Multi Repository

Plugin Marketplace

Dashboard

Cloud Runner