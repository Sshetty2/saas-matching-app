from textwrap import dedent


def format_software_info(software_info):
    """Format software info into a readable string."""
    vendor = software_info.get("vendor", "N/A")
    product = software_info.get("product", "N/A")
    version = software_info.get("version", "N/A")

    return dedent(
        f"""
        Vendor: {vendor}
        Product: {product}
        Version: {version}
        """
    )


def format_product_matches(product_matches):
    """Format product matches into a readable string."""
    if not product_matches:
        return "No matches found."

    result = []
    for i, match in enumerate(product_matches, 1):
        vendor = match.get("vendor", "N/A")
        product = match.get("product", "N/A")

        result.append(
            dedent(
                f"""
                Top Match #{i}:
                Vendor: {vendor}
                Product: {product}
                """
            )
        )

    return "\n".join(result)


def format_cpe_results(cpe_results):
    """Format CPE results into a readable string."""
    results = []

    for cpe_result in cpe_results:
        vendor = cpe_result.get("Vendor", "N/A")
        product = cpe_result.get("Product", "N/A")
        version = cpe_result.get("Version", "N/A")
        cpe_id = cpe_result.get("ConfigurationsName", "N/A")
        db_cpe_id = cpe_result.get("CPEConfigurationID", "N/A")

        results.append(
            dedent(
                f"""
                ID: {db_cpe_id}
                CPE: {cpe_id}
                Vendor: {vendor}
                Product: {product}
                Version: {version}
                """
            )
        )

    return "\n".join(results)
