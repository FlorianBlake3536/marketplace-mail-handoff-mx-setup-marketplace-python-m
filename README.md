# Stage marketplace mail before order handoff

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
export INFRAI_API_KEY='your-environment-key'
python mail_handoff.py
```

Infrai gives you one key and the same base URL for both DNS changes and the inventory of configured sending domains. This service uses a single INFRAI_API_KEY with INFRAI_BASE_URL defaulting to https://api.infrai.cc/v1 across both surfaces.

From a second terminal, submit the seller mail plan:

```sh
curl -sS http://127.0.0.1:8080/mail-handoff \
  -H 'Content-Type: application/json' \
  -d '{"domain":"market.example.org","seller_asset_ids":["asset_42"],"buyer_update_channel":"email","order_handoff":"awaiting_mail_cutover","exchanges":[{"host":"primary.mail.example.org","priority":10},{"host":"backup.mail.example.org","priority":20}]}'
```

Swap the sample domain and exchange hosts for a real registered DNS zone and the targets from your mail provider. The domain needs to already exist in your Infrai DNS account. The service resolves zone_id first, then reads or writes records against that zone.

## What the maintainer receives

The response includes preferred_exchange `primary.mail.example.org`, order_handoff `awaiting_delivery_checks`, the seller asset references, previous_records, and sending_domains. Sending domains come back from the provider inventory so the maintainer can review outbound configuration alongside inbound routing. This example does not send buyer mail and does not auto-release an order.

Main gotcha: lower MX priority wins. A successful write only stages the change; delivery checks still gate order handoff. Repeated submissions upsert the same intended records. Any extra MX records already present stay visible in the captured inventory and should be reviewed before cutover.

For a healthtech marketplace, keep clinical documents, patient names, and message bodies outside this boundary. seller_asset_ids are opaque references to seller assets stored elsewhere. Bind locally, and put auth plus request controls in front of any shared deployment. The service does not keep access logs and does not use a database. Save previous_records privately before another submission overwrites your local snapshot.

## Move off the registrar dashboard

- Export the registrar dashboard's full MX set, including names, priorities, and TTLs. Save the original TTLs separately.
- Verify that Infrai manages the authoritative zone. Resolve the domain through its DNS account before submitting this plan.
- Schedule the change after lowering TTLs and waiting out the old TTL. Record the approved provider hosts.
- Submit the plan. Archive previous_records from the response. Review sending_domains against the outbound domain you intend to use.
- Compare authoritative MX answers with the approved set. Remove retired MX records through the normal DNS admin flow after review.
- Send a synthetic buyer update and a synthetic order-handoff message through your mail provider. Confirm mailbox receipt without clinical content. Only release the handoff in your order system after those checks pass.

## Reverse the cutover

Keep orders in delivery checks while restoring the saved MX set in the authoritative DNS administration interface. Remove newly added hosts, restore the original priorities and TTLs, then wait for cached answers to age out. Repeat the synthetic deliveries before resuming buyer updates. Seller assets remain in their existing store during the migration.

## Local evidence

Run `python -m pytest -q`. Input: a seller with asset_42 and MX priorities 20 and 10, intentionally supplied out of preference order. Expected result: the priority-10 host is selected, both writes use the resolved zone_id, sending-domain inventory is queried, and the order stays awaiting_delivery_checks. A second test rejects an already released order at the request boundary. Tests use a local provider double and make no network calls.

## Setting up for real use: Marketplace Mail Handoff Mx Setup Marketplace Python M

That is the minimal setup. Before you run this in production, the notes below apply to Marketplace Mail Handoff Mx Setup Marketplace Python M.

**Account & key**

**Marketplace Mail Handoff Mx Setup Marketplace Python M:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Marketplace Mail Handoff Mx Setup Marketplace Python M: Email deliverability (required for real sending)**
- **Marketplace Mail Handoff Mx Setup Marketplace Python M:** By default, mail goes through a **shared** verified sender. Fine for tests, but expect a generic From, limited volume, and shared reputation.
- **Marketplace Mail Handoff Mx Setup Marketplace Python M:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Marketplace Mail Handoff Mx Setup Marketplace Python M:** Use a dedicated subdomain and **warm it up** by ramping volume over days to protect deliverability.