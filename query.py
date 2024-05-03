#!/usr/bin/env python

# Slightly hacky script to clean up crypto team project board

from typing import List

import attrs
import os

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

tok = os.environ["GITHUB_TOKEN"]

PROJECT_ID = "PVT_kwDOAM0swc4AMDGh"

client = Client(
    transport=(
        AIOHTTPTransport(
            url="https://api.github.com/graphql",
            headers={"Authorization": f"Bearer {tok}"},
        )
    ),
    fetch_schema_from_transport=True,
)


@attrs.define
class Item:
    id: str
    url: str
    closedAt: str


def get_issues():
    pagination_token = ""
    while pagination_token is not None:
        query = gql(
            """
        query( $pag: String ) {
          organization(login: "element-hq") {
            projectV2(number: 76) {
              items(first: 10, after: $pag ) {
                pageInfo {
                  endCursor
                }
                nodes {
                  type
                  id
                  databaseId

                  content {
                    ... on Issue {
                      closed
                      closedAt
                      url
                      labels(first:100) {
                        nodes {
                          id
                          name
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        )
        result = client.execute(query, variable_values={"pag": pagination_token})
        items = result["organization"]["projectV2"]["items"]
        pagination_token = items["pageInfo"]["endCursor"]
        yield from items["nodes"]


def archive_item(item: Item) -> None:
    print(f"Archiving {item.url} from {item.closedAt}")
    query = gql(
        """
      mutation( $itemid: ID!, $projectid: ID! ) {
        archiveProjectV2Item(input:{
          itemId: $itemid
          projectId: $projectid
        }) {
          clientMutationId
        }
      }
    """
    )
    client.execute(query, variable_values={"itemid": item.id, "projectid": PROJECT_ID})


items: List[Item] = []

for item in get_issues():
    try:
        if item["type"] != "ISSUE":
            continue
        if not item["content"]["closed"]:
            continue
        labels = [lbl["name"] for lbl in item["content"]["labels"]["nodes"]]
        if "Z-UISI" not in labels:
            continue
        items.append(Item(
            item["id"],
            item["content"]["url"],
            item["content"]["closedAt"],
        ))
    except Exception:
        raise Exception(f"error parsing item {item}")

for item in items:
    archive_item(item)
