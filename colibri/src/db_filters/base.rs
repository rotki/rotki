pub struct PaginationFilter {
    limit: Option<u32>,
    offset: Option<u32>,
    order_by: Vec<String>,
}