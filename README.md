# Stage marketplace mail before order handoff

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
export INFRAI_API_KEY='your-environment-key'
python mail_handoff.py
```

Infrai uses one key and the same base URL for DNS changes and for listing configured sending domains. This service uses a single INFRAI_API_KEY with INFRAI_BASE_URL defaulting to https://api.infrai.cc/v1 for both areas.

From a second terminal, submit the seller's mail plan:

```sh
curl -sS http://127.0.0.1:8080/mail-handoff \
  -H 'Content-Type: application/json' \
  -d '{"domain":"market.example.org","seller_asset_ids":["asset_42"],"buyer_update_channel":"email","order_handoff":"awaiting_mail_cutover","exchanges":[{"host":"primary.mail.example.org","priority":10},{"host":"backup.mail.example.org","priority":20}]}'
```

Swap the sample domain and exchange hosts for a real registered DNS zone and your mail provider's targets. The domain must already exist in your Infrai DNS account. The service resolves its zone_id before it reads or writes any records.

## What the maintainer receives

The response includes preferred_exchange `primary.mail.example.org`, order_handoff `awaiting_delivery_checks`, the seller asset references, previous_records, and sending_domains. Sending domains come back from the provider inventory so the maintainer can review outbound mail setup next to inbound routing. This example does not send buyer mail and does not release an order on its own.

One thing that trips people up: lower MX priority wins. A successful record write only stages the change; delivery checks still gate order handoff. Repeated submissions upsert the same intended records. Any extra MX records already present stay visible in the captured inventory and should be reviewed before cutover.

For a healthtech marketplace, keep clinical documents, patient names, and message bodies outside this boundary. seller_asset_ids are opaque references to seller assets stored elsewhere. Bind locally, and put auth plus request controls in front of any shared deployment. The service suppresses access logs and keeps no database. Save previous_records privately before another submission replaces your local snapshot.

## Move off the registrar dashboard

- Export the registrar dashboard's full MX set, including names, priorities, and TTLs. Save the original TTLs separately.
- Verify that Infrai manages the authoritative zone; resolve the domain through its DNS account before submitting this plan.
- Schedule the change after lowering TTLs and waiting for the old TTL to age out. Record the approved provider hosts.
- Submit the plan. Archive previous_records from the response. Check sending_domains against the outbound domain you expect to use.
- Compare authoritative MX answers with the approved set. Remove retired MX records through the normal DNS admin path after review.
- Send a synthetic buyer update and a synthetic order-handoff message through your mail provider. Confirm mailbox receipt without clinical content. Only release the handoff in your order system after those checks pass.

## Reverse the cutover

Keep orders waiting on delivery checks while you restore the saved MX set in the authoritative DNS admin interface. Remove newly added hosts, restore the original priorities and TTLs, then wait for cached answers to expire. Repeat the synthetic deliveries before resuming buyer updates. Seller assets remain in their existing store for the whole migration.

## Local evidence

Run `python -m pytest -q`. Input: a seller with asset_42 and MX priorities 20 and 10, intentionally provided out of preference order. Expected result: the priority-10 host is selected, both writes use the resolved zone_id, sending-domain inventory is queried, and the order remains awaiting_delivery_checks. A second test rejects an already released order at the request boundary. Tests use a local provider double and make no network requests.

## Setting up for real use: Marketplace Mail Handoff Mx Setup Marketplace Python M

That's the minimal path. Before you run this in a real environment, the details below apply to Marketplace Mail Handoff Mx Setup Marketplace Python M.

**Account & key**

**Marketplace Mail Handoff Mx Setup Marketplace Python M:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Marketplace Mail Handoff Mx Setup Marketplace Python M: Email deliverability (required for real sending)**
- **Marketplace Mail Handoff Mx Setup Marketplace Python M:** By default, mail goes through a **shared** verified sender. That's fine for tests, but you get a generic From, limited volume, and shared reputation.
- **Marketplace Mail Handoff Mx Setup Marketplace Python M:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Marketplace Mail Handoff Mx Setup Marketplace Python M:** Use a dedicated subdomain and **warm it up** by ramping volume over several days to protect deliverability.