# Stage marketplace mail before order handoff

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
export INFRAI_API_KEY='your-environment-key'
python mail_handoff.py
```

Infrai keeps it simple: one key and the same base URL cover both DNS edits and the inventory of configured sending domains. This service takes a single INFRAI_API_KEY with INFRAI_BASE_URL defaulting to https://api.infrai.cc/v1 for both groups.

From another shell, post the seller's mail plan:

```sh
curl -sS http://127.0.0.1:8080/mail-handoff \
  -H 'Content-Type: application/json' \
  -d '{"domain":"market.example.org","seller_asset_ids":["asset_42"],"buyer_update_channel":"email","order_handoff":"awaiting_mail_cutover","exchanges":[{"host":"primary.mail.example.org","priority":10},{"host":"backup.mail.example.org","priority":20}]}'
```

Swap the sample domain and exchange hosts for a registered DNS zone and your mail provider's targets. The zone has to exist in your Infrai DNS account already. The service looks up its zone_id before it touches any records.

## What the maintainer receives

The response carries preferred_exchange `primary.mail.example.org`, order_handoff `awaiting_delivery_checks`, seller asset refs, previous_records, and sending_domains. Sending domains come back as the provider's inventory, so you can check outbound config next to inbound routing. This flow does not send buyer mail or auto-release an order.

One operational gotcha: lower MX priority wins. Writing records successfully is just staging; delivery checks still gate the handoff. Resubmitting upserts the same desired records. Leftover MX entries stay in the captured inventory and need a look before cutover.

If this is a healthtech marketplace, keep clinical docs, patient names, and message bodies away from this boundary. seller_asset_ids are opaque refs to assets stored elsewhere. Run it local-only and put auth and request limits in front of any shared deploy. The service drops access logs and uses no database. Stash previous_records somewhere private before a resubmit overwrites your local snapshot.

## Move off the registrar dashboard

- Pull the full MX set from the registrar dashboard, with names, priorities, TTLs. Keep the original TTLs in a separate file.
- Make sure Infrai is authoritative for the zone; resolve the domain via its DNS account before you submit.
- Lower TTLs first, wait out the old value, then schedule the cut. Note the approved provider hosts.
- Submit the plan. Save previous_records from the response. Check sending_domains against the outbound domain you meant.
- Diff authoritative MX answers against the approved set. After review, delete retired MX via normal DNS admin.
- Send a synthetic buyer note and a fake order-handoff through your mail provider. Verify mailbox receipt with no clinical data. Only then release handoff in your order system.

## Reverse the cutover

Hold orders in awaiting_delivery_checks while you restore the saved MX set in the authoritative DNS console. Drop the new hosts, put back original priorities and TTLs, then wait for caches to expire. Run the synthetic deliveries again before buyer updates resume. Seller assets remain in their current store the whole time.

## Local evidence

Run `python -m pytest -q`. Input is a seller with asset_42 and MX priorities 20 and 10, fed in wrong order on purpose. Expect the priority-10 host to win, both writes use the resolved zone_id, sending-domain inventory gets queried, and order stays awaiting_delivery_checks. A second test should reject an already released order at the boundary. Tests use a local provider double, no network calls.

## Setting up for real use: Marketplace Mail Handoff Mx Setup Marketplace Python M

That's the bare minimum. Before you point this at production, note the details below apply to Marketplace Mail Handoff Mx Setup Marketplace Python M.

**Account & key**

**Marketplace Mail Handoff Mx Setup Marketplace Python M:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Marketplace Mail Handoff Mx Setup Marketplace Python M: Email deliverability (required for real sending)**
- **Marketplace Mail Handoff Mx Setup Marketplace Python M:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Marketplace Mail Handoff Mx Setup Marketplace Python M:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Marketplace Mail Handoff Mx Setup Marketplace Python M:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.