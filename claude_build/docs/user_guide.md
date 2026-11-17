# User Guide — Offline Engineering-Docs Assistant

**What it is:** a tool that answers questions about your engineering
documents (specs, test reports, change notices, manuals) using a local AI
model. It never leaves your machine and never uses the internet.

## How to ask a good question

- **Be specific.** "What is the vibration test duration for the RADAR-100?"
  works much better than "tell me about vibration."
- **Name the document or section if you know it.** "What does section 3.2.2
  of the RADAR-100 spec require?" narrows the search.
- **Ask one thing at a time.** Split "what changed between Rev A and Rev B"
  into "what is the operating temperature in Rev A" and "...in Rev B" if the
  combined answer looks incomplete.
- **Use exact part/method numbers when you have them** (e.g. "P/N 7741-0032",
  "Method 514.8") — the tool keeps an exact keyword index specifically for
  these, in addition to its meaning-based search.

## How to check a source

Every answer ends with one or more citations in the form
`[DOCUMENT_NAME.pdf, p.N]`. Before you rely on an answer:

1. Open the named document and go to page N.
2. Confirm the sentence or table the tool quoted is actually there.
3. If the document has multiple revisions, check you're looking at the
   revision the tool cited — the tool tries to prefer the newest revision
   automatically, but always double-check on anything safety-critical.
4. If the answer cites a document marked **CONFIDENTIAL** or **RESTRICTED**,
   handle it per your normal document-handling rules — the tool surfaces the
   marking but does not enforce access control itself.

## What the tool cannot do

- It cannot answer anything that isn't in the ingested documents — it will
  say **"Not found in the documents"** rather than guess. If you get that
  answer, the information may exist in a document that hasn't been ingested
  yet, or it may genuinely not be documented.
- It cannot verify that a document is current, complete, or officially
  released — it only reflects what was fed into it.
- It cannot replace engineering judgment. Treat answers as a fast pointer to
  the right page, not as an approved engineering decision.
- It cannot connect to the internet, and should not be asked to — it has no
  way to look anything up beyond what you ingested.

## Where to go for help

If the tool gives an unexpected answer, try rephrasing the question more
specifically, or check with the engineer who maintains the document set
whether the source document is actually in the ingested set
(`data/real/` and `data/synthetic/`).
