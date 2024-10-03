#!/usr/bin/env python
#
# Slightly hacky script to clean up crypto team project board
# Looks for "Done" and "Tombstoned" issues which have not been updated in the last 6 months, and archives them.

from datetime import datetime, timedelta
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
    updatedAt: datetime


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
                  updatedAt

                  status: fieldValueByName(name: "Status") {
                    ... on ProjectV2ItemFieldSingleSelectValue {
                      name
                    }
                  }

                  content {
                    ... on Issue {
                      closed
                      closedAt
                      url
                      """
#                      labels(first:100) {
#                        nodes {
#                          id
#                          name
#                        }
#                      }
                      """
                    }
                    ... on PullRequest {
                      closed
                      closedAt
                      url
                    }
                    ... on DraftIssue {
                      title
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
    print(f"Archiving {item.url}")
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
        if item["type"] == "DRAFT_ISSUE":
            title = item["content"]["title"]
        else:
            title = item["content"]["url"]

        # ignore items which are not 'Done' or 'Tombstoned'
        status = item["status"]["name"]
        if status not in ('Done', 'Tombstoned'):
            continue

        #print(f'Considering {status} {item["type"]} {title}: {item}')

        # python pre-3.11 doesn't support trailing TZ identifier
        updatedAt = datetime.fromisoformat(item["updatedAt"].removesuffix('Z'))

        # ignore items updated too recently
        if datetime.now()-updatedAt < timedelta(days=180):
            #print("updated too recently");
            continue

        #labels = [lbl["name"] for lbl in item["content"]["labels"]["nodes"]]
        #if "Z-UISI" not in labels:
        #    continue

        print(f"Will archive {status} {item['type']} {title}: last updated {updatedAt}")

        items.append(Item(
            item["id"],
            title,
            updatedAt,
        ))
    except Exception:
        raise Exception(f"error parsing item {item}")

for item in items:
    archive_item(item)
