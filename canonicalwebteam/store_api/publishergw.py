from os import getenv
from pprint import pprint
from requests import Session

from canonicalwebteam.store_api.base import Base


PUBLISHERGW_URL = getenv("PUBLISHERGW_URL", "https://api.charmhub.io")
VALID_NAMESPACE = ["charms", "snaps"]
CHARMSTORE_VALID_PACKAGE_TYPES = ["charm", "bundle"]

class PublisherGW(Base):
    def __init__(self, name_space: str, session=Session()):
        super().__init__(session)
        self.name_space = name_space #for urls that has namespace
        self.config = {
            1: {"base_url": f"{PUBLISHERGW_URL}/v1"},
            2: {"base_url": f"{PUBLISHERGW_URL}/v2"},
        }

    def get_endpoint_url(self, endpoint: str, version: int = 1, has_name_space=True):
        base_url = self.config[version]["base_url"]
        if has_name_space:
            return f"{base_url}/{self.name_space}/{endpoint}"
        return f"{base_url}/{endpoint}"
        
    # SEARCH
    def find(
        self,
        query="",
        category="",
        publisher="",
        type=None,
        provides=[],
        requires=[],
        fields=[],
    ):
        """
        Given a search term, return an array of matching search results.
        v2 API only.

        Documentation: https://api.snapcraft.io/docs/charms.html#charm_find
        Endpoint: https://api.charmhub.io/v2/charms/find
        """
        url = self.get_endpoint_url("find", 2)
        headers = self.config[2].get("headers")
        params = {
            "q": query,
            "category": category,
            "publisher": publisher,
            "type": type,
        }
        if fields:
            params["fields"] = ",".join(fields)

        if provides:
            params["provides"] = ",".join(provides)

        if requires:
            params["requires"] = ",".join(requires)

        return self.process_response(
            self.session.get(url, params=params, headers=headers)
        )

    # CATEGORIES
    def get_categories(self, api_version=2, type="shared"):
        """
        Documentation: https://api.snapcraft.io/docs/categories.html
        Endpoint: https://api.charmhub.io/v2/{name_space}/categories
        """
        url = self.get_endpoint_url("categories", api_version)
        pprint("inside_device")
        x = self.session.get(url, headers=self.config[api_version].get("headers"), params={"type": type})
        pprint(x)
        return self.process_response(
            self.session.get(
                url,
                headers=self.config[api_version].get("headers"),
                params={"type": type},
            )
        )

    # AUTH AND MACAROONS
    def _get_authorization_header(self, publisher_auth):
        """
        Return the formatted Authorization header for the publisher API.
        """
        return {"Authorization": f"Macaroon {publisher_auth}"}

    def get_macaroon(self):
        """
        Return existing macaroons for the authenticated account.
        Documentation: https://api.charmhub.io/docs/default.html#get_macaroon
        Endpoint URL: [GET] https://api.charmhub.io/v1/tokens
        """
        response = self.session.get(url=self.get_endpoint_url("tokens"))

        return self.process_response(response)["macaroon"]

    def issue_macaroon(self, permissions, description=None, ttl=None):
        """
        Return a bakery v2 macaroon to be discharged by Candid.
        Documentation: https://api.charmhub.io/docs/default.html#issue_macaroon
        Endpoint URL: [POST] https://api.charmhub.io/v1/tokens
        """
        data = {"permissions": permissions}

        if description:
            data["description"] = description

        if ttl:
            data["ttl"] = ttl

        response = self.session.post(
            url=self.get_endpoint_url("tokens"),
            json=data,
        )
        return self.process_response(response)["macaroon"]

    def exchange_macaroons(self, issued_macaroon):
        """
        Return an exchanged snapstore-only authentication macaroon.
        Documentation:
            https://api.charmhub.io/docs/default.html#exchange_macaroons
        Endpoint URL: [POST] https://api.charmhub.io/v1/tokens/exchange
        """

        response = self.session.post(
            url=self.get_endpoint_url("tokens/exchange"),
            headers={"Macaroons": issued_macaroon},
            json={},
        )

        return self.process_response(response)["macaroon"]
    
    # nyt
    def exchange_dashboard_macaroons(self, publisher_auth):
        """
        Exchange dashboard.snapcraft.io SSO discharged macaroons
        Documentation:
            https://api.charmhub.io/docs/default.html#exchange_dashboard_macaroons
        Endpoint: [POST] https://api.charmhub.io/v1/tokens/dashboard/exchange
        """
        response = self.session.post(
            url=self.get_endpoint_url("tokens/dashboard/exchange"),
            headers=self._get_authorization_header(publisher_auth),
            json={},
        )

        return self.process_response(response)["macaroon"]

    def macaroon_info(self, publisher_auth):
        """
        Return information about the authenticated macaroon token.
        Documentation: https://api.charmhub.io/docs/default.html#macaroon_info
        Endpoint URL: [GET] https://api.charmhub.io/v1/tokens/whoami
        """
        response = self.session.get(
            url=self.get_endpoint_url("tokens/whoami"),
            headers=self._get_authorization_header(publisher_auth),
        )

        return self.process_response(response)
    
    # nyt
    def whoami(self, publisher_auth):
        """
        Return information about the authenticated macaroon token.
        Documentation: 'DEPRECATED'
        Endpoint URL: [GET] https://api.charmhub.io/v1/whoami
        """
        response = self.session.get(
            url=self.get_endpoint_url("whoami"),
            headers=self._get_authorization_header(publisher_auth),
        )

        return self.process_response(response)
    
    # PACKAGES MANAGEMENT
    def get_account_packages(
        self,
        publisher_auth,
        package_type,
        include_collaborations=False,
        status=None,
    ):
        """
        Return publisher packages
        Documentation: https://api.charmhub.io/docs/default.html
        Endpoint URL: [GET] https://api.charmhub.io/v1/{package_type}

        Args:
            publisher_auth: Serialized macaroon to consume the API.
            package_type: Type of packages to obtain.
            include_collaborations (optional): Include shared charms
            status (optional): Only packages with the given status

        Returns:
            A list of packages
        """

        if self.name_space == "charms" and package_type not in CHARMSTORE_VALID_PACKAGE_TYPES:
            raise ValueError( 
                "Invalid package type. Expected one of: %s"
                % CHARMSTORE_VALID_PACKAGE_TYPES
            )

        params = {}

        if include_collaborations:
            params["include-collaborations"] = "true"
        response = self.session.get(
            url=self.get_endpoint_url(package_type, has_name_space=False),
            headers=self._get_authorization_header(publisher_auth),
            params=params,
        )
        packages = self.process_response(response)["results"]

        if status:
            packages = [p for p in packages if p["status"] == status]

        return packages

    def get_package_metadata(self, publisher_auth, package_name):
        """
        Get general metadata for a package.
        Documentation:
            https://api.charmhub.io/docs/default.html#package_metadata
        Endpoint URL: [GET] https://api.charmhub.io/v1/{namespace}/{package_name}
        namespace: charm for both charms and bundles
        package_name: Package name

        Args:
            publisher_auth: Serialized macaroon to consume the API.
            package_type: Type of packages to obtain.

        Returns:
            Package general metadata
        """
        response = self.session.get(
            url=self.get_endpoint_url(package_name),
            headers=self._get_authorization_header(publisher_auth),
        )

        return self.process_response(response)["metadata"]

    def update_package_metadata(
        self, publisher_auth, package_type, name, data
    ):
        """
        Update general metadata for a package.
        Documentation:
            https://api.charmhub.io/docs/default.html#update_package_metadata
        Endpoint URL: [PATCH]
            https://api.charmhub.io/v1/{namespace}/<name>
        namespace: charm for both charms and bundles
        name: Package name

        Args:
            publisher_auth: Serialized macaroon to consume the API.
            package_type: Type of packages to obtain.
            name: Package name
            data: Dict with changes to apply

        Returns:
            Package general metadata with changes applied
        """

        if self.name_space == "charm" and package_type not in CHARMSTORE_VALID_PACKAGE_TYPES:
            raise ValueError(
                "Invalid package type. Expected one of: %s"
                % CHARMSTORE_VALID_PACKAGE_TYPES
            )

        response = self.session.patch(
            url=self.get_endpoint_url(f"{package_type}/{name}"),
            headers=self._get_authorization_header(publisher_auth),
            json=data,
        )

        return self.process_response(response)["metadata"]

    def register_package_name(self, publisher_auth, data):
        """
        Register a package name.
        Documentation: https://api.charmhub.io/docs/default.html#register_name
        Endpoint URL: [POST] https://api.charmhub.io/v1/{namespace}

        Args:
            publisher_auth: Serialized macaroon to consume the API.
            data: Dict with name, type and visibility of the package

        Returns:
            Newly registered name id
        """

        response = self.session.post(
            url=self.get_endpoint_url(f"{self.name_space}", has_name_space=False),
            headers=self._get_authorization_header(publisher_auth),
            json=data,
        )

        return self.process_response(response)

    def unregister_package_name(self, publisher_auth, package_name):
        """
        Unregister a package name.
        Documentation:
            https://api.charmhub.io/docs/default.html#unregister_package
        Endpoint URL: [DELETE] https://api.charmhub.io/v1/charm/<name>

        Args:
            publisher_auth: Serialized macaroon to consume the API.
            name: Name of the package to unregister
        Returns:
            The package name ID if successful
            Otherwise, returns an error list
        """
        url = self.get_endpoint_url(package_name)
        response = self.session.delete(
            url=url,
            headers=self._get_authorization_header(publisher_auth),
        )
        return response

    def get_charm_libraries(self, package_name, package_type):
        """
        Get libraries for a charm.
        Documentation:
            https://api.charmhub.io/docs/libraries.html#fetch_libraries
        Endpoint URL: [POST] https://api.charmhub.io/v1/{package_type}/libraries/bulk
        """
        ur = self.get_endpoint_url(f"{package_type}/libraries/bulk", has_name_space=False)
        pprint(ur)
        response = self.session.post(
            url=self.get_endpoint_url(f"{package_type}/libraries/bulk", has_name_space=False),
            json=[{"charm-name": package_name}],
        )

        return self.process_response(response)

    def get_charm_library(self, charm_name, library_id, api_version=None):
        """
        Get library metadata and content
        Documentation:
            https://api.charmhub.io/docs/libraries.html#fetch_library
        Endpoint URL: [GET]
        https://api.charmhub.io/v1/charm/libraries/{charm_name}/{library_id}

        Args:
            charm_name: Name of the charm
            library_id: ID of the library
            api_version: API version to use
        """
        params = {}

        if api_version is not None:
            params["api"] = api_version
        response = self.session.get(
            url=self.get_endpoint_url(
                f"charm/libraries/{charm_name}/{library_id}", has_name_space=False
            ),
            params=params,
        )

        return self.process_response(response)

    def get_releases(self, publisher_auth, package_name):
        """
        List of all releases for a package.
        Documentation:
            https://api.charmhub.io/docs/default.html#list_releases
        Endpoint URL: [GET]
            https://api.charmhub.io/v1/{namespace}/<name>/releases

        Args:
            publisher_auth: Serialized macaroon to consume the API.
            name: Name of the package
        """
        response = self.session.get(
            url=self.get_endpoint_url(f"{package_name}/releases"),
            headers=self._get_authorization_header(publisher_auth),
        )
        return self.process_response(response)

    def get_item_details(self, name, channel=None, fields=[], api_version=2):
        """
        Documentation: https://api.snapcraft.io/docs/info.html
        Endpoint: [GET]
            https://api.charmhub.io/api/v2/{name_space}/info/{package_name}
        """
        url = self.get_endpoint_url("info/" + name, api_version)
        params = {"fields": ",".join(fields)}

        if channel:
            params["channel"] = channel

        return self.process_response(
            self.session.get(
                url,
                params=params,
                headers=self.config[api_version].get("headers"),
            )
        )

    # COLLABORATORS
    def get_collaborators(self, publisher_auth, package_name):
        """
        Get collaborators (accepted invites) for the given package.
        Documentation:
            https://api.charmhub.io/docs/collaborator.html#get_collaborators
        Endpoint URL: [GET]
            https://api.charmhub.io/v1/{name_space}/{package_name}/collaborators

        Args:
            publisher_auth: Serialized macaroon to consume the API.
            name_space: Namespace of the package, can be 'snap' or 'charm'.
            package_name: Name of the package
        """
        response = self.session.get(
            url=self.get_endpoint_url(f"{package_name}/collaborators"),
            headers=self._get_authorization_header(publisher_auth),
        )
        return self.process_response(response)

    def get_pending_invites(self, publisher_auth, package_name):
        """
        Get pending collaborator invites for the given package.
        Documentation:
            https://api.charmhub.io/docs/collaborator.html#get_pending_invites
        Endpoint URL: [GET]
            https://api.charmhub.io/v1/{name_space}/{package_name}/collaborators/invites

        Args:
            publisher_auth: Serialized macaroon to consume the API.
            name_space: Namespace of the package, can be 'snap' or 'charm'.
            package_name: Name of the package
        """
        response = self.session.get(
            url=self.get_endpoint_url(f"{package_name}/collaborators/invites"),
            headers=self._get_authorization_header(publisher_auth),
        )
        return self.process_response(response)

    def invite_collaborators(self, publisher_auth, package_name, emails):
        """
        Invite one or more collaborators for a package.
        Documentation:
            https://api.charmhub.io/docs/collaborator.html#invite_collaborators
        Endpoint URL: [POST]
            https://api.charmhub.io/v1/{name_space}/{package_name}/collaborators/invites

        Args:
            publisher_auth: Serialized macaroon to consume the API.
            name_space: Namespace of the package, can be 'snap' or 'charm'.
            package_name: Name of the package
            emails: List of emails to invite
        """
        payload = {"invites": []}

        for email in emails:
            payload["invites"].append({"email": email})

        response = self.session.post(
            url=self.get_endpoint_url(f"{package_name}/collaborators/invites"),
            headers=self._get_authorization_header(publisher_auth),
            json=payload,
        )
        return self.process_response(response)

    def revoke_invites(self, publisher_auth, package_name, emails):
        """
        Revoke invites to the specified emails for the package.
        Documentation:
            https://api.charmhub.io/docs/collaborator.html#revoke_invites
        Endpoint URL: [POST]
            https://api.charmhub.io/v1/{namespace}/{package_name}/collaborators/invites/revoke

        Args:
            publisher_auth: Serialized macaroon to consume the API.
            name: Name of the package
            emails: List of emails to revoke
        """
        payload = {"invites": []}

        for email in emails:
            payload["invites"].append({"email": email})

        response = self.session.post(
            url=self.get_endpoint_url(
                f"{package_name}/collaborators/invites/revoke"
            ),
            headers=self._get_authorization_header(publisher_auth),
            json=payload,
        )
        return response

    def accept_invite(self, publisher_auth, package_name, token):
        """
        Accept a collaborator invite.
        Documentation:
            https://api.charmhub.io/docs/collaborator.html#accept_invite
        Endpoint URL: [POST]
            https://api.charmhub.io/v1/{name_space}/{package_name}/collaborators/invites/accept

        Args:
            publisher_auth: Serialized macaroon to consume the API.
            name: Name of the package
            token: Invite token
        """
        response = self.session.post(
            url=self.get_endpoint_url(
                f"{package_name}/collaborators/invites/accept"
            ),
            headers=self._get_authorization_header(publisher_auth),
            json={"token": token},
        )
        return response

    def reject_invite(self, publisher_auth, package_name, token):
        """
        Reject a collaborator invite.
        Documentation:
            https://api.charmhub.io/docs/collaborator.html#reject_invite
        Endpoint URL: [POST]
            https://api.charmhub.io/v1/{name_space}/{package_name}/collaborators/invites/reject

        Args:
            publisher_auth: Serialized macaroon to consume the API.
            name: Name of the package
            token: Invite token
        """
        response = self.session.post(
            url=self.get_endpoint_url(
                f"{package_name}/collaborators/invites/reject"
            ),
            headers=self._get_authorization_header(publisher_auth),
            json={"token": token},
        )
        return response

    # TRACKS
    def create_track(
        self,
        publisher_auth,
        package_name,
        track_name,
        version_pattern=None,
        auto_phasing_percentage=None,
    ):
        """
        Create a track for an artefact base on the artefact's guardrail pattern.
        Documentation: https://api.charmhub.io/docs/default.html#create_tracks
        Endpoint URL: [POST]
            https://api.charmhub.io/v1/charm/{package_name}/tracks

        Args:
            publisher_auth: Serialized macaroon to consume the API.
            charm_name: Name of the charm
            track_name: Name of the track
            version_pattern: Version pattern for the track (optional)
            auto_phasing_percentage: phasing percentage for track (optional)
        """

        payload = {
            "name": track_name,
            "version-pattern": version_pattern,
            "automatic-phasing-percentage": auto_phasing_percentage,
        }
        response = self.session.post(
            url=self.get_endpoint_url(f"{package_name}/tracks"),
            headers=self._get_authorization_header(publisher_auth),
            json=[payload],
        )
        return response

    # MODEL SERVICE ADMIN
    def get_store_models(self, publisher_auth, store_id):
        """
        Documentation:
            https://api.charmhub.io/docs/model-service-admin.html#read_models
        Endpoint: [GET] https://api.charmhub.io/v1/brand/{store_id}/model
        """
        response = self.session.get(
            url=self.get_endpoint_url(f"brand/{store_id}/model", has_name_space=False),
            headers=self._get_authorization_header(publisher_auth),
        )

        return self.process_response(response)

    def create_store_model(self, publisher_auth, store_id, name, api_key=None):
        """
        Documentation:
            https://api.charmhub.io/docs/model-service-admin.html#create_model
        Endpoint: [POST] https://api.charmhub.io/v1/brand/{store_id}/model
        """
        if api_key:
            payload = {"name": name, "api-key": api_key, "series": "16"}
        else:
            payload = {"name": name, "series": "16"}
        response = self.session.post(
            url=self.get_endpoint_url(f"brand/{store_id}/model", has_name_space=False),
            headers=self._get_authorization_header(publisher_auth),
            json=payload,
        )

        return self.process_response(response)

    def update_store_model(self, publisher_auth, store_id, model_name, api_key):
        """
        Doucumentation:
            https://api.charmhub.io/docs/model-service-admin.html#update_model
        Endpoint: [PATCH]
            https://api.charmhub.io/v1/brand/{store_id}/model/{model_name}
        """
        response = self.session.patch(
            url=self.get_endpoint_url(
                f"brand/{store_id}/model/{model_name}", has_name_space=False
            ),
            headers=self._get_authorization_header(publisher_auth),
            json={"api-key": api_key},
        )

        return self.process_response(response)

    def get_store_model_policies(self, publisher_auth, store_id, model_name):
        """
        Documentation:
            https://api.charmhub.io/docs/model-service-admin.html#read_serial_policies
        Endpoint: [GET]
            https://api.charmhub.io/v1/brand/{store_id}/model/<model_name>/serial_policy
        """
        response = self.session.get(
            url=self.get_endpoint_url(
                f"brand/{store_id}/model/{model_name}/serial_policy", has_name_space=False
            ),
            headers=self._get_authorization_header(publisher_auth),
        )

        return self.process_response(response)

    def create_store_model_policy(
        self, publisher_auth, store_id, model_name, signing_key
    ):
        """
        Documentation:
            https://api.charmhub.io/docs/model-service-admin.html#create_serial_policy
        Endpoint: [POST]
            https://api.charmhub.io/v1/brand/{store_id}/model/{model_name}/serial_policy
        """
        response = self.session.post(
            url=self.get_endpoint_url(
                f"brand/{store_id}/model/{model_name}/serial_policy", has_name_space=False
            ),
            headers=self._get_authorization_header(publisher_auth),
            json={"signing-key-sha3-384": signing_key},
        )

        return self.process_response(response)

    def delete_store_model_policy(
        self, publisher_auth, store_id, model_name, revision
    ):
        """
        Documentation:
            https://api.charmhub.io/docs/model-service-admin.html#delete_serial_policy
        Endpoint: [DELETE]
            https://api.charmhub.io/v1/brand/{store_id}/model/{model_name}/serial_policy/{serial_policy_revision}
        """
        response = self.session.delete(
            url=self.get_endpoint_url(
                f"brand/{store_id}/model/{model_name}/serial_policy/{revision}", has_name_space=False
            ),
            headers=self._get_authorization_header(publisher_auth),
        )

        return response

    def get_store_signing_keys(self, publisher_auth, store_id):
        """
        Documentation:
            https://api.charmhub.io/docs/model-service-admin.html#read_signing_keys
        Endpoint: [GET] https://api.charmhub.io/v1/brand/{store_id}/signing_key
        """
        headers = self._get_authorization_header(publisher_auth)
        url = self.get_endpoint_url(
            f"brand/{store_id}/signing_key", has_name_space=False
        )
        response = self.session.get(
            url=url,
            headers=headers,
        )
        return self.process_response(response)

    def create_store_signing_key(self, publisher_auth, store_id, name):
        """
        Documentation:
            https://api.charmhub.io/docs/model-service-admin.html#create_signing_key
        Endpoint: [POST]
            https://api.charmhub.io/v1/brand/{store_id}/signing_key
        """
        headers = self._get_authorization_header(publisher_auth)
        url = self.get_endpoint_url(
            f"brand/{store_id}/signing_key", has_name_space=False
        )
        response = self.session.post(
            url=url,
            headers=headers,
            json={"name": name},
        )
        return self.process_response(response)

    def delete_store_signing_key(
        self, publisher_auth, store_id, signing_key_sha3_384
    ):
        """
        Documentation:
            https://api.charmhub.io/docs/model-service-admin.html#delete_signing_key
        Endpoint: [DELETE]
            https://api.charmhub.io/v1/brand/{store_id}/signing_key/<signing_key_sha3_384}
        """
        headers = self._get_authorization_header(publisher_auth)
        url = self.get_endpoint_url(
            f"brand/{store_id}/signing_key/{signing_key_sha3_384}", has_name_space=False
        )
        response = self.session.delete(
            url=url,
            headers=headers,
        )

        return response

    def get_brand(self, publisher_auth, store_id):
        """
        Documentation:
            https://api.charmhub.io/docs/model-service-admin.html#read_brand
        Endpoint: [GET] https://api.charmhub.io/v1/brand/{store_id}
        """
        headers = self._get_authorization_header(publisher_auth)
        url = self.get_endpoint_url(f"brand/{store_id}", has_name_space=False)
        response = self.session.get(
            url=url,
            headers=headers,
        )

        return self.process_response(response)

    # FEATURED SNAP AUTOMATION
    def delete_featured_snaps(self, publisher_auth, packages):
        """
        Documentation: (link to spec)
            https://docs.google.com/document/d/1UAybxuZyErh3ayqb4nzL3T4BbvMtnmKKEPu-ixcCj_8
        Endpoint: [DELETE] https://api.charmhub.io/v1/snap/featured
        """
        headers = self._get_authorization_header(publisher_auth)
        url = self.get_endpoint_url("featured")
        response = self.session.delete(
            url=url,
            headers=headers,
            json=packages
        )
        return response

    def update_featured_snaps(self, publisher_auth, snaps):
        """
        Documentation: (link to spec)
            https://docs.google.com/document/d/1UAybxuZyErh3ayqb4nzL3T4BbvMtnmKKEPu-ixcCj_8
        Endpoint: [PUT] https://api.charmhub.io/v1/{name_space}/featured
        """
        headers = self._get_authorization_header(publisher_auth)
        url = self.get_endpoint_url("featured")
        response = self.session.put(
            url=url,
            headers=headers,
            json=snaps,
        )
        return response

